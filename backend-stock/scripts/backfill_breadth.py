"""
market_breadth_daily 1회성 백필 스크립트.

최근 30 거래일치만 채운다 — 5년 전체 백필은 하지 않는다(breadth는 과거
스냅샷의 실사용 가치가 낮고, price_daily 5년 전량을 훑는 비용이 크다).
시장별로 순차 실행하며, 날짜당 1 트랜잭션으로 커밋한다(중간 실패 시
그 날짜만 롤백되고 이전에 커밋된 날짜는 남는다).

── 왜 asyncpg를 직접 쓰는가 (SyncSessionLocal/psycopg2를 쓰지 않는 이유) ──
이 프로젝트에서 로컬 머신 → Railway Postgres 프록시(zephyr.proxy.rlwy.net)
연결은 psycopg2로는 타임아웃난다 — scripts/restore_history.py 서두 주석에
이미 문서화된 기존 이슈이며, backend-stock/.env.prod에도 "SSL 없이(ssl=False)
접속해야 함" / "sslmode=disable 은 타임아웃 발생 — asyncpg 사용 권장"이라고
명시돼 있다. 실제로 psycopg2.connect(..., connect_timeout=8)로 재현 확인함.
반면 asyncpg(ssl=False)는 로컬에서도 정상 연결된다. 그래서 이 스크립트는
market_breadth_daily.compute_market_breadth()(SyncSessionLocal 기반, 운영
cron 코드 경로)를 호출하지 않고 fomobot.services.breadth의 순수 함수만
재사용해 DB I/O를 asyncpg로 직접 재구현했다 — restore_history.py/
check_rankings.py와 동일한 패턴이다.

── 실행 방법 ──

1) 로컬에서 실행 (asyncpg 직접 연결이라 실제로 가능함 — psycopg2 문제 없음):
     cd backend-stock
     .venv\\Scripts\\python.exe scripts\\backfill_breadth.py
     .venv\\Scripts\\python.exe scripts\\backfill_breadth.py --market kospi
     .venv\\Scripts\\python.exe scripts\\backfill_breadth.py --dry-run
   .env.prod가 있으면 자동으로 로드한다(DATABASE_URL, 운영 DB).

2) market_breadth_daily 테이블이 아직 배포되지 않았다면(마이그레이션은
   web 서비스 재배포 시 `alembic upgrade head`로 자동 적용됨):
   이 스크립트는 실행 전 테이블 존재를 확인하고, 없으면 안내 메시지만
   출력하고 종료한다(exit 1). web 서비스가 재배포될 때까지 기다렸다가
   다시 실행하면 된다.

3) 로컬 실행이 막힌 환경이라면 Railway 콘솔에서 실행 (이 프로젝트의
   기존 관례 — scripts/check_rankings.py 상단 주석 참조):
   Railway Dashboard > 아무 서비스(예: web) 선택 > 우측 상단 메뉴에서
   콘솔/쉘 진입 후:
     python scripts/backfill_breadth.py
   (web 서비스 컨테이너에는 이미 DATABASE_URL 등 환경변수가 주입되어
   있으므로 .env.prod 로딩 로직은 자동으로 건너뛴다.)

   또는 임시로 cron 서비스 하나의 Command를 아래로 바꿔 1회 트리거 후
   원래 Command로 되돌리는 방법도 가능하다(railway.toml 상단 주석에
   설명된 기존 cron 서비스 추가/관리 방식과 동일):
     python scripts/backfill_breadth.py

옵션:
  --market {kospi,nasdaq,both}  기본 both
  --days N                       기본 30 (최근 N 거래일)
  --dry-run                      실제 저장 없이 계산 결과만 출력
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import date
from pathlib import Path

# .env, .env.prod 파일에서 환경 변수 로드 (이미 환경변수로 주입된 값은 덮어쓰지 않음 —
# Railway 컨테이너 안에서 실행할 때는 이 루프가 사실상 no-op이 된다)
for _env_name in [".env", ".env.prod"]:
    _env_file = Path(__file__).parent.parent / _env_name
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncpg  # noqa: E402

from fomobot.services.breadth import classify_breadth, is_excluded_nasdaq_security  # noqa: E402

logging.basicConfig(
    level="INFO",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL이 환경변수/.env.prod에 없습니다.")
# asyncpg는 SQLAlchemy용 +asyncpg 접두사를 이해하지 못하므로 제거.
# 쿼리스트링(예: .env의 ?ssl=disable)도 제거 — asyncpg.connect()에 ssl=False를
# 별도 kwarg로 명시하는데, DSN에 ssl 파라미터가 같이 있으면
# "parameter ssl cannot be changed now" 에러가 난다.
DB_URL = DB_URL.replace("postgresql+asyncpg://", "postgresql://").split("?")[0]


async def _table_exists(conn: asyncpg.Connection, table_name: str) -> bool:
    return await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
        table_name,
    )


async def _get_recent_trading_days(conn: asyncpg.Connection, market: str, n: int) -> list[date]:
    """market 기준 최근 n개 거래일을 오름차순으로 반환 (price_daily 실측 기준)."""
    rows = await conn.fetch(
        "SELECT DISTINCT date FROM price_daily WHERE market = $1 ORDER BY date DESC LIMIT $2",
        market, n,
    )
    return sorted(r["date"] for r in rows)


async def _get_prev_trading_day(conn: asyncpg.Connection, market: str, before: date) -> date | None:
    return await conn.fetchval(
        "SELECT MAX(date) FROM price_daily WHERE market = $1 AND date < $2",
        market, before,
    )


async def _get_breadth_price_pairs(
    conn: asyncpg.Connection, market: str, date_curr: date, date_prev: date | None,
) -> list[dict]:
    """crud.get_breadth_price_pairs_sync와 동일한 명시적 LEFT JOIN 로직(LAG 미사용)."""
    if date_prev is None:
        rows = await conn.fetch(
            "SELECT ticker, close_adj AS close_curr, volume AS volume_curr "
            "FROM price_daily WHERE market=$1 AND date=$2",
            market, date_curr,
        )
        return [
            {"ticker": r["ticker"], "close_curr": r["close_curr"],
             "volume_curr": r["volume_curr"], "close_prev": None}
            for r in rows
        ]
    rows = await conn.fetch(
        """
        SELECT curr.ticker AS ticker,
               curr.close_adj AS close_curr,
               curr.volume AS volume_curr,
               prev.close_adj AS close_prev
        FROM price_daily curr
        LEFT JOIN price_daily prev
          ON prev.ticker = curr.ticker
         AND prev.market = curr.market
         AND prev.date = $3
        WHERE curr.market = $1 AND curr.date = $2
        """,
        market, date_curr, date_prev,
    )
    return [dict(r) for r in rows]


async def _get_security_names(conn: asyncpg.Connection, market: str, tickers: list[str]) -> dict[str, str]:
    if not tickers:
        return {}
    rows = await conn.fetch(
        "SELECT ticker, name FROM securities_master WHERE market=$1 AND ticker = ANY($2::text[])",
        market, tickers,
    )
    return {r["ticker"]: r["name"] for r in rows}


async def _compute_and_upsert_one_day(
    conn: asyncpg.Connection, market: str, target_date: date, dry_run: bool,
) -> dict:
    date_prev = await _get_prev_trading_day(conn, market, target_date)
    rows = await _get_breadth_price_pairs(conn, market, target_date, date_prev)

    if market == "nasdaq" and rows:
        tickers = [r["ticker"] for r in rows]
        name_map = await _get_security_names(conn, market, tickers)
        rows = [r for r in rows if not is_excluded_nasdaq_security(name_map.get(r["ticker"]))]

    pairs = [(r["close_curr"], r["close_prev"]) for r in rows]
    counts = classify_breadth(pairs)
    halted = sum(1 for r in rows if r["volume_curr"] == 0)
    total = counts["advancers"] + counts["decliners"] + counts["unchanged"] + counts["excluded"]

    record = {
        "market": market, "date": target_date,
        "advancers": counts["advancers"], "decliners": counts["decliners"],
        "unchanged": counts["unchanged"], "excluded": counts["excluded"],
        "halted": halted, "total": total,
    }

    if not dry_run:
        async with conn.transaction():  # 날짜당 1 트랜잭션
            await conn.execute(
                """
                INSERT INTO market_breadth_daily
                    (market, date, advancers, decliners, unchanged, excluded, halted, total)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (market, date) DO UPDATE SET
                    advancers = EXCLUDED.advancers,
                    decliners = EXCLUDED.decliners,
                    unchanged = EXCLUDED.unchanged,
                    excluded = EXCLUDED.excluded,
                    halted = EXCLUDED.halted,
                    total = EXCLUDED.total
                """,
                market, target_date,
                counts["advancers"], counts["decliners"], counts["unchanged"],
                counts["excluded"], halted, total,
            )

    return record


async def main_async(markets: list[str], days: int, dry_run: bool) -> None:
    conn = await asyncpg.connect(DB_URL, ssl=False)
    try:
        if not await _table_exists(conn, "market_breadth_daily"):
            logger.error(
                "market_breadth_daily 테이블이 아직 없습니다. "
                "web 서비스 재배포(alembic upgrade head 자동 실행)를 기다린 뒤 다시 실행하세요."
            )
            sys.exit(1)

        total_saved = 0
        failed: list[tuple[str, date, str]] = []

        for market in markets:  # 시장별 순차 실행
            trading_days = await _get_recent_trading_days(conn, market, days)
            logger.info(
                "%s: 최근 %d거래일 백필 시작 (%s ~ %s)",
                market.upper(), len(trading_days),
                trading_days[0] if trading_days else "-",
                trading_days[-1] if trading_days else "-",
            )
            for i, d in enumerate(trading_days, 1):
                try:
                    record = await _compute_and_upsert_one_day(conn, market, d, dry_run)
                    total_saved += 0 if dry_run else 1
                    logger.info(
                        "[%s %d/%d] %s: 상승 %d / 하락 %d / 보합 %d / 제외 %d / 총 %d%s",
                        market.upper(), i, len(trading_days), d,
                        record["advancers"], record["decliners"], record["unchanged"],
                        record["excluded"], record["total"],
                        " (dry-run, 저장 안 함)" if dry_run else "",
                    )
                except Exception as exc:
                    logger.error("실패: %s %s — %s", market, d, exc)
                    failed.append((market, d, str(exc)))

        logger.info("완료: %d일 저장, 실패 %d건", total_saved, len(failed))
        if failed:
            for market, d, err in failed:
                logger.warning("  실패: %s %s: %s", market, d, err)
            sys.exit(1)
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="market_breadth_daily 1회성 백필 (최근 N거래일)")
    parser.add_argument("--market", choices=["kospi", "nasdaq", "both"], default="both")
    parser.add_argument("--days", type=int, default=30, help="백필할 최근 거래일 수 (기본 30)")
    parser.add_argument("--dry-run", action="store_true", help="계산만 하고 저장하지 않음")
    args = parser.parse_args()

    markets = ["kospi", "nasdaq"] if args.market == "both" else [args.market]
    asyncio.run(main_async(markets, args.days, args.dry_run))


if __name__ == "__main__":
    main()
