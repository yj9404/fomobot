"""
공유 카드 엔드포인트.

  GET /api/share/{market}/{ticker}?from=&to=      — 카드 수치 JSON
  GET /api/og/{market}/{ticker}.png?from=&to=     — 카드 PNG (1200×630)

두 엔드포인트는 services/share.build_share_snapshot 하나로 검증·계산한다.
수치는 URL로 받지 않는다 — 입력은 market, ticker, from, to뿐이다.

캐시:
  성공 응답은 같은 URL이면 내용이 같으므로 immutable(1년).
  오류 응답은 no-store — "to가 최신일보다 늦음"은 다음 거래일이면 정상 요청이 되고,
  플래그 해제된 종목도 다시 열려야 하므로 오류를 캐시하면 안 된다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from fomobot.db.session import get_async_session
from fomobot.schemas.share import ShareResponse
from fomobot.services.og_card import render_card
from fomobot.services.share import ShareError, ShareSnapshot, build_share_snapshot

router = APIRouter(prefix="/api", tags=["Share"])

IMMUTABLE = "public, max-age=31536000, immutable"


async def _snapshot_or_error(
    session: AsyncSession, market: str, ticker: str, from_raw: str | None, to_raw: str | None
) -> ShareSnapshot:
    try:
        return await build_share_snapshot(session, market, ticker, from_raw, to_raw)
    except ShareError as e:
        raise HTTPException(
            status_code=e.status_code, detail=e.detail, headers={"Cache-Control": "no-store"}
        )


@router.get(
    "/share/{market}/{ticker}",
    response_model=ShareResponse,
    summary="공유 카드 수치 — 종목·기간 buy-and-hold 스냅샷",
)
async def share_endpoint(
    market: str,
    ticker: str,
    response: Response,
    # from/to는 필수지만 Optional로 받아 직접 검증한다 — FastAPI 기본 422 대신
    # no-store가 붙은 400을 내기 위함.
    from_raw: str | None = Query(None, alias="from", description="시작 거래일 (YYYY-MM-DD)"),
    to_raw: str | None = Query(None, alias="to", description="끝 거래일 (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_async_session),
):
    snap = await _snapshot_or_error(session, market, ticker, from_raw, to_raw)
    response.headers["Cache-Control"] = IMMUTABLE
    return ShareResponse(
        market=snap.market,
        ticker=snap.ticker,
        name=snap.name,
        from_date=snap.from_date,
        to_date=snap.to_date,
        start_price=snap.start_price,
        end_price=snap.end_price,
        return_pct=snap.return_pct,
        mdd_pct=snap.mdd_pct,
        principal=snap.principal,
        end_value=snap.end_value,
        currency=snap.currency,
    )


@router.get(
    "/og/{market}/{ticker}.png",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
    summary="공유 카드 이미지 — 1200×630 PNG",
)
async def og_image_endpoint(
    market: str,
    ticker: str,
    from_raw: str | None = Query(None, alias="from", description="시작 거래일 (YYYY-MM-DD)"),
    to_raw: str | None = Query(None, alias="to", description="끝 거래일 (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_async_session),
):
    snap = await _snapshot_or_error(session, market, ticker, from_raw, to_raw)
    png = await run_in_threadpool(render_card, snap)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": IMMUTABLE},
    )
