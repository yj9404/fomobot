"""
로컬 개발용 더미 랭킹 데이터 시드 스크립트.

운영 환경에서는 실제 배치(collect_kospi/collect_nasdaq → compute_rankings)로 대체.
실행: uv run python scripts/seed_dummy.py
"""

import random
from datetime import date

from fomobot.db.crud import upsert_ranking_snapshots_sync
from fomobot.db.session import SyncSessionLocal

SNAPSHOT_DATE = date.today()

PERIODS = ["1d", "7d", "30d", "90d", "365d", "1825d"]

KOSPI_STOCKS = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("035420", "NAVER"),
    ("005380", "현대차"),
    ("000270", "기아"),
    ("035720", "카카오"),
    ("051910", "LG화학"),
    ("006400", "삼성SDI"),
    ("068270", "셀트리온"),
    ("105560", "KB금융"),
    ("055550", "신한지주"),
    ("032830", "삼성생명"),
    ("028260", "삼성물산"),
    ("003550", "LG"),
    ("034730", "SK"),
    ("017670", "SK텔레콤"),
    ("030200", "KT"),
    ("096770", "SK이노베이션"),
    ("009150", "삼성전기"),
    ("018260", "삼성에스디에스"),
    ("011170", "롯데케미칼"),
    ("024110", "기업은행"),
    ("000100", "유한양행"),
    ("207940", "삼성바이오로직스"),
    ("090430", "아모레퍼시픽"),
    ("010130", "고려아연"),
    ("004020", "현대제철"),
    ("009540", "HD한국조선해양"),
    ("012330", "현대모비스"),
    ("066570", "LG전자"),
]

NASDAQ_STOCKS = [
    ("NVDA", "NVIDIA"),
    ("AAPL", "Apple"),
    ("MSFT", "Microsoft"),
    ("AMZN", "Amazon"),
    ("GOOGL", "Alphabet"),
    ("META", "Meta"),
    ("TSLA", "Tesla"),
    ("AVGO", "Broadcom"),
    ("AMD", "AMD"),
    ("NFLX", "Netflix"),
    ("ADBE", "Adobe"),
    ("QCOM", "Qualcomm"),
    ("INTC", "Intel"),
    ("CSCO", "Cisco"),
    ("TXN", "Texas Instruments"),
    ("AMAT", "Applied Materials"),
    ("MU", "Micron"),
    ("LRCX", "Lam Research"),
    ("KLAC", "KLA Corp"),
    ("MRVL", "Marvell"),
    ("PANW", "Palo Alto Networks"),
    ("CRWD", "CrowdStrike"),
    ("SNOW", "Snowflake"),
    ("DDOG", "Datadog"),
    ("TEAM", "Atlassian"),
    ("ZS", "Zscaler"),
    ("OKTA", "Okta"),
    ("COIN", "Coinbase"),
    ("PYPL", "PayPal"),
    ("ABNB", "Airbnb"),
]

# 기간별 수익률 범위 (현실적인 범위)
PERIOD_RETURN_RANGE = {
    "1d":    (-5.0,   8.0),
    "7d":    (-10.0,  20.0),
    "30d":   (-15.0,  40.0),
    "90d":   (-20.0,  80.0),
    "365d":  (-30.0,  200.0),
    "1825d": (-40.0,  500.0),
}


def _make_records(market: str, stocks: list[tuple[str, str]], top: int = 20) -> list[dict]:
    records = []
    for period in PERIODS:
        ret_min, ret_max = PERIOD_RETURN_RANGE[period]
        # 상위 종목일수록 수익률이 높도록 정렬
        returns = sorted(
            [random.uniform(ret_min, ret_max) for _ in range(len(stocks))],
            reverse=True,
        )
        for rank, ((ticker, name), ret) in enumerate(zip(stocks, returns), start=1):
            if rank > top:
                break
            vol = abs(ret) * random.uniform(0.3, 0.8)
            mdd = -abs(ret) * random.uniform(0.1, 0.5)
            excess = ret - random.uniform(-5.0, 15.0)
            records.append({
                "snapshot_date": SNAPSHOT_DATE,
                "market": market,
                "period": period,
                "rank": rank,
                "ticker": ticker,
                "name": name,
                "return_pct": round(ret, 2),
                "mdd_pct": round(mdd, 2),
                "volatility_annualized_pct": round(vol, 2),
                "excess_return_pct": round(excess, 2),
            })
    return records


def main() -> None:
    random.seed(42)
    records = _make_records("kospi", KOSPI_STOCKS) + _make_records("nasdaq", NASDAQ_STOCKS)

    with SyncSessionLocal() as session:
        upsert_ranking_snapshots_sync(session, records)

    print(f"더미 데이터 삽입 완료: {len(records)}건 (기준일: {SNAPSHOT_DATE})")
    print("  - KOSPI:", len(PERIODS) * min(20, len(KOSPI_STOCKS)), "건")
    print("  - NASDAQ:", len(PERIODS) * min(20, len(NASDAQ_STOCKS)), "건")


if __name__ == "__main__":
    main()
