"""
공유 카드 스냅샷 — 검증 + 계산.

GET /api/share(JSON)와 GET /api/og(PNG)가 이 모듈 하나를 공유한다. 두 엔드포인트가
같은 입력에 대해 다른 숫자를 내는 일이 없도록 검증·계산은 여기서만 한다.

URL 하나 = 내용 하나 원칙:
  입력은 market, ticker, from, to 네 개뿐이고 수치는 전부 서버가 계산한다.
  from/to는 그 종목 시계열에 실제로 존재하는 날짜여야 하며, 가까운 거래일로
  스냅하지 않는다 — 스냅하면 서로 다른 URL이 같은 내용을 가리키게 된다.

수익률·MDD는 buy-and-hold 기준이다(from 종가에 전량 매수, to 종가까지 보유).
close_adj 시계열을 날짜순으로 가져와 compute_quote_metrics(검색 quote API와 동일
함수)로 계산한다 — LAG 윈도우 함수를 쓰지 않는다.
"""

import re
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import (
    get_corporate_action_flag_status_async,
    get_last_trading_day_async,
    get_price_series_async,
    get_security_async,
)
from fomobot.services.calculator import compute_quote_metrics

SHARE_MARKETS = ("kospi", "nasdaq")

# 시장 통화 그대로 표시한다. NASDAQ은 USD 시계열이라 원화 원금을 쓰면 환율이
# 빠진 숫자가 되므로 달러 원금을 쓴다.
PRINCIPAL = {"kospi": 1_000_000, "nasdaq": 10_000}
CURRENCY = {"kospi": "KRW", "nasdaq": "USD"}

# 오염된 close_adj 시계열 종목 — 랭킹 배치와 같은 기준으로 공유도 막는다.
# 막지 않으면 오염된 수치가 R2 영구 캐시에 고정된다.
BLOCKED_FLAG_STATUSES = ("excluded", "pending")

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ShareError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class ShareSnapshot:
    market: str
    ticker: str
    name: str
    from_date: date
    to_date: date
    start_price: float
    end_price: float
    return_pct: float
    mdd_pct: float
    principal: int
    end_value: int
    currency: str


def parse_share_date(value: str | None, field: str) -> date:
    """YYYY-MM-DD만 허용한다. 다른 표기(20251015 등)를 받아주면 같은 내용에
    URL이 여러 개 생긴다."""
    if value is None or not _DATE_RE.match(value):
        raise ShareError(400, f"{field}는 YYYY-MM-DD 형식이어야 합니다.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ShareError(400, f"{field}가 올바른 날짜가 아닙니다.")


async def build_share_snapshot(
    session: AsyncSession,
    market: str,
    ticker: str,
    from_raw: str | None,
    to_raw: str | None,
) -> ShareSnapshot:
    if market not in SHARE_MARKETS:
        raise ShareError(404, "지원하지 않는 시장입니다.")

    from_date = parse_share_date(from_raw, "from")
    to_date = parse_share_date(to_raw, "to")
    if from_date >= to_date:
        raise ShareError(400, "from은 to보다 앞선 날짜여야 합니다.")

    ticker = ticker.upper()
    security = await get_security_async(session, market, ticker)
    if security is None:
        raise ShareError(404, "존재하지 않는 종목입니다.")

    flag_status = await get_corporate_action_flag_status_async(session, market, ticker)
    if flag_status in BLOCKED_FLAG_STATUSES:
        raise ShareError(404, "데이터 정정 중인 종목이라 공유 카드를 만들 수 없습니다.")

    latest = await get_last_trading_day_async(session, market)
    if latest is None or to_date > latest:
        raise ShareError(400, "to가 최신 데이터일보다 늦습니다.")

    rows = await get_price_series_async(session, market, ticker, from_date, to_date)
    if len(rows) < 2 or rows[0][0] != from_date or rows[-1][0] != to_date:
        raise ShareError(404, "from/to가 이 종목의 거래일이 아닙니다.")

    start_price = rows[0][1]
    end_price = rows[-1][1]
    if not start_price or start_price <= 0:
        raise ShareError(404, "시작가가 유효하지 않습니다.")

    prices = pd.Series(
        [p for _, p in rows],
        index=pd.DatetimeIndex([d for d, _ in rows]),
    )
    metrics = compute_quote_metrics(prices)

    principal = PRINCIPAL[market]
    return ShareSnapshot(
        market=market,
        ticker=ticker,
        name=security.name or ticker,
        from_date=from_date,
        to_date=to_date,
        start_price=start_price,
        end_price=end_price,
        return_pct=metrics["return_pct"],
        mdd_pct=metrics["mdd_pct"],
        principal=principal,
        end_value=round(principal * end_price / start_price),
        currency=CURRENCY[market],
    )
