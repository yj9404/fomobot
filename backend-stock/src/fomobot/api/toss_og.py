"""
토스 미니앱 공유 카드 이미지 — Share.createLink의 ogImageUrl로 쓴다.

  GET /api/og/toss/stock/{market}/{ticker}.png?chart=&date=YYYY-MM-DD
  GET /api/og/toss/rankings/{market}.png?period=&cap=&order=&date=YYYY-MM-DD

웹 카드(/api/og, Worker /og/*)와 달리 Railway가 직접 응답한다. Worker는 웹 도메인에
있어 토스 번들에 그 주소를 넣을 수 없기 때문이다(check-toss-bundle 금지 토큰).

URL 하나 = 내용 하나:
  date로 기준일을 고정하고 스냅하지 않는다(거래일·스냅샷일이 아니면 404).
  그래서 성공 응답은 immutable로 캐시하고, 오류는 no-store — 다음 거래일이면
  정상이 되는 요청(미래 date)이나 정정이 끝난 종목이 오류 상태로 굳지 않게 한다.

차트 구간(chart):
  상세 화면에서 고른 구간 그대로 카드 차트를 그린다. 빠지면 1년 — chart가 생기기 전에
  퍼진 카드 URL(?date=&v=1)이 같은 내용을 유지한다.

카드 버전(v):
  immutable 캐시라 카드 디자인이나 렌더링 버그를 고쳐도 이미 퍼진 URL은 갱신되지 않는다.
  프론트가 ogImageUrl에 &v=<카드 버전>을 붙이고, 디자인을 바꾸면 그 값을 올려 새 URL을 만든다.
  서버는 v를 읽지 않는다 — 응답 내용에 영향이 없고 캐시 키 역할만 한다.
"""

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.crud import get_nearest_snapshot_date
from fomobot.db.session import get_async_session
from fomobot.services.og_card_toss import (
    CAP_LABEL,
    CHART_PERIODS,
    DEFAULT_CHART,
    ORDER_LABEL,
    PERIOD_LABEL,
    render_toss_rankings_card,
    render_toss_stock_card,
)
from fomobot.services.share import SHARE_MARKETS
from fomobot.services.stock_detail import StockDetailError, build_stock_detail

router = APIRouter(prefix="/api/og/toss", tags=["Share"])

IMMUTABLE = "public, max-age=31536000, immutable"
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PNG_RESPONSES = {200: {"content": {"image/png": {}}}}


def _error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail, headers={"Cache-Control": "no-store"})


def _parse_date(value: str | None) -> date:
    if value is None or not _DATE_RE.match(value):
        raise _error(400, "date는 YYYY-MM-DD 형식이어야 합니다.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise _error(400, "date가 올바른 날짜가 아닙니다.")


def _check_market(market: str) -> None:
    if market not in SHARE_MARKETS:
        raise _error(404, "지원하지 않는 시장입니다.")


def _png(content: bytes) -> Response:
    return Response(content=content, media_type="image/png", headers={"Cache-Control": IMMUTABLE})


@router.get(
    "/stock/{market}/{ticker}.png",
    response_class=Response,
    responses=_PNG_RESPONSES,
    summary="토스 종목 공유 카드 — 1200×600 PNG",
)
async def toss_stock_card_endpoint(
    market: str,
    ticker: str,
    chart: str = Query(DEFAULT_CHART, description="7d|30d|90d|365d|1825d — 카드 차트 구간"),
    # 필수지만 Optional로 받아 직접 검증한다 — FastAPI 기본 422 대신 no-store가 붙은 400을 내기 위함.
    date_raw: str | None = Query(None, alias="date", description="기준 거래일 (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_async_session),
):
    _check_market(market)
    if chart not in CHART_PERIODS:
        raise _error(400, "chart 값을 확인하세요.")
    as_of = _parse_date(date_raw)
    try:
        detail = await build_stock_detail(session, market, ticker, as_of=as_of)
    except StockDetailError as e:
        raise _error(e.status_code, e.detail)
    if detail.status == "correcting":
        raise _error(404, "데이터 정정 중인 종목이라 공유 카드를 만들 수 없습니다.")
    if detail.status != "ok":
        raise _error(404, "기준일에 시세가 없는 종목입니다.")
    return _png(await run_in_threadpool(render_toss_stock_card, detail, chart))


@router.get(
    "/rankings/{market}.png",
    response_class=Response,
    responses=_PNG_RESPONSES,
    summary="토스 순위 공유 카드 — 조건과 기준일만 담은 1200×600 PNG",
)
async def toss_rankings_card_endpoint(
    market: str,
    period: str | None = Query(None, description="1d|7d|30d|90d|365d|1825d"),
    cap: str | None = Query(None, description="all|small|mid|large"),
    order: str | None = Query(None, description="desc|asc"),
    date_raw: str | None = Query(None, alias="date", description="랭킹 스냅샷 기준일 (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_async_session),
):
    _check_market(market)
    if period not in PERIOD_LABEL or cap not in CAP_LABEL or order not in ORDER_LABEL:
        raise _error(400, "period, cap, order 값을 확인하세요.")
    as_of = _parse_date(date_raw)
    # 카드에는 수치가 없지만 존재하지 않는 기준일로 카드를 만들지 않도록 스냅샷 존재를 확인한다.
    if await get_nearest_snapshot_date(session, market, period, as_of) != as_of:
        raise _error(404, "해당 기준일의 랭킹이 없습니다.")
    png = await run_in_threadpool(render_toss_rankings_card, market, period, cap, order, as_of)
    return _png(png)
