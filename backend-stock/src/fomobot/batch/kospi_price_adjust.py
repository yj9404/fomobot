"""
KOSPI 가격 기준(basis) 소급 보정.

KOSPI는 KRX 원 종가를 저장한다(collect_kospi.py). 원 종가만으로는 분할·병합·감자·
무상/유상증자 권리락이 있는 날 과거 시계열과 기준이 어긋난다. KRX는 그런 날의
기준가(= 종가 − 전일대비)를 새 주식 기준으로 다시 계산해 게시하므로,
"기준가 ÷ DB의 D-1 종가"가 1이 아니면 그 비율만큼 D 이전 이력을 소급 조정한다.
결과는 KRX·네이버 수정주가와 같은 정의다 — 분할·병합·감자·증자 반영,
현금배당 미반영(현금배당은 기준가를 바꾸지 않는다).

분류 — f = 기준가 / D-1 close_adj, s = 상장주식수(D) / 상장주식수(D-1):

  | 조건                          | 판정                          | 계수 |
  |-------------------------------|-------------------------------|------|
  | |f−1| ≤ 1e-6                  | 이벤트 없음                   | —    |
  | s ≈ 1, 0.1 ≤ f < 1            | 권리락(무상·유상증자), 자동   | f    |
  | s ≈ 1, 그 외                  | 보류                          | —    |
  | s ≠ 1, |f·s−1| < 1%           | 분할·병합·감자, 자동          | f    |
  | s ≠ 1, 그 외                  | 보류                          | —    |

계수는 항상 f다. 보정 후 D-1 종가가 기준가와 같아져서, 이벤트 당일 수익률에 가짜 변동이
생기지 않고 같은 날을 다시 돌리면 이벤트가 0건이다(멱등성). 1/s는 분할·병합·감자 판정의
교차검증(|f·s−1| < 1%)에만 쓴다. 기준가는 호가 단위로 반올림되므로 f는 정확한 배수가 아닐
수 있다(예: 1,553×5 = 7,765 → 기준가 7,770, f = 5.0032). 소각·CB 전환처럼 주식 수만 바뀌고
기준가가 그대로인 날은 첫 행(f = 1)에 걸려 이벤트가 아니다.

자동 적용: D 이전 모든 행의 시가·고가·저가·종가 × 계수, 거래량 ÷ 계수(반올림).
시가총액은 그대로 둔다 — 과거 수동 정정과 같은 방식이고, 원래 그날의 실제 값이다.
역연산(revert_price_basis_event)으로 되돌릴 수 있다. 거래량은 반올림 때문에 근사치로 돌아온다.

기록: corporate_action_flag(ticker unique)에 남긴다.
  - 기존 행이 없으면 자동 적용은 status=resolved, 보류는 status=pending으로 새로 만든다.
  - 기존 행이 있으면 detected_signal에 내역을 덧붙인다. 자동 적용은 status·reason을
    건드리지 않는다(정지 중 pending 종목은 사람이 재개를 확인할 때까지 계속 제외).
    보류는 resolved였던 종목을 pending으로 되돌려 랭킹에서 다시 뺀다.
"""
import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from fomobot.db.models import CorporateActionFlag

logger = logging.getLogger(__name__)

REL_TOL = 1e-6        # 기준가 = D-1 종가 판정, 주식 수 불변 판정(상대오차)
BASIS_TOL = 0.01      # f·s ≈ 1 판정(상대오차 1%)
RIGHTS_MIN_F = 0.1    # 권리락 계수 하한 — 이보다 작으면 단일 권리락으로 보기 어렵다

KIND_SHARE_BASIS = "share_basis"   # 분할·병합·감자
KIND_RIGHTS = "rights"             # 무상·유상증자 권리락
KIND_HOLD = "hold"
KIND_OVERRIDE = "override"         # 사람이 계수를 지정(재적재 스크립트 --override). 자동 분류가 보류한 종목용


@dataclass(frozen=True)
class PriceBasisEvent:
    ticker: str
    date: date
    base: float            # KRX 기준가 = 종가 − 전일대비
    prev: float            # DB의 D-1 close_adj
    f: float               # base / prev
    s: float | None        # 상장주식수 D / D-1 (어느 한쪽이 없으면 None)
    kind: str              # KIND_SHARE_BASIS | KIND_RIGHTS | KIND_HOLD
    factor: float | None   # D 이전 가격에 곱할 계수(보류면 None)

    @property
    def is_auto(self) -> bool:
        return self.factor is not None

    def signal_text(self) -> str:
        s_txt = f"{self.s:.6f}" if self.s is not None else "null"
        factor_txt = f"{self.factor:.6f}" if self.factor is not None else "null"
        return (
            f"[basis {self.date.isoformat()}] kind={self.kind} f={self.f:.6f} s={s_txt} "
            f"factor={factor_txt} base={self.base:g} prev={self.prev:.4f}"
        )


def _rel_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(abs(a), abs(b))


def classify_price_basis(
    ticker: str,
    d: date,
    close: float,
    cmpprevdd: float,
    prev_close: float | None,
    shares: int | None,
    shares_prev: int | None,
) -> PriceBasisEvent | None:
    """한 종목·한 날짜의 기준가 변동을 분류한다. 이벤트가 없거나 판단할 근거가 없으면 None."""
    if prev_close is None or prev_close <= 0 or close <= 0:
        return None  # D-1 행 없음(신규상장·재상장 등) 또는 가격 없음 — 비교 대상 아님

    base = close - cmpprevdd
    if base <= 0:
        return None
    if _rel_close(base, prev_close, REL_TOL):
        return None

    f = base / prev_close
    s = (shares / shares_prev) if shares and shares_prev else None

    def make(kind: str, factor: float | None) -> PriceBasisEvent:
        return PriceBasisEvent(ticker, d, base, prev_close, f, s, kind, factor)

    if s is None:
        return make(KIND_HOLD, None)  # 주식 수를 몰라 분류 불가

    if _rel_close(s, 1.0, REL_TOL):
        if RIGHTS_MIN_F <= f < 1:
            return make(KIND_RIGHTS, f)
        return make(KIND_HOLD, None)

    if abs(f * s - 1) < BASIS_TOL:
        return make(KIND_SHARE_BASIS, f)
    return make(KIND_HOLD, None)


def detect_price_basis_events(
    d: date,
    snapshot: dict[str, dict],
    prev_close: dict[str, float],
    prev_shares: dict[str, int],
) -> list[PriceBasisEvent]:
    """
    수집일 D의 전종목 스냅샷에서 기준가 변동 종목을 찾는다.

    snapshot    : {ticker: {"close", "cmpprevdd", "list_shrs"}} — KRX D일 원값
    prev_close  : {ticker: close_adj} — DB의 D-1 거래일 행(명시적 날짜 조회)
    prev_shares : {ticker: list_shrs} — KRX D-1일 상장주식수
    """
    events = []
    for ticker, row in snapshot.items():
        ev = classify_price_basis(
            ticker, d,
            close=row["close"],
            cmpprevdd=row["cmpprevdd"],
            prev_close=prev_close.get(ticker),
            shares=row.get("list_shrs"),
            shares_prev=prev_shares.get(ticker),
        )
        if ev is not None:
            events.append(ev)
    return events


# 정수 나눗셈·정밀도 손실을 피하려고 계수와 거래량을 NUMERIC으로 명시 캐스팅한다.
# 가격 컬럼은 double precision이라 결과는 할당 시 다시 double로, 거래량은 bigint로 변환된다.
_ADJUST_SQL = text(
    "UPDATE price_daily SET "
    "open = open * CAST(:g AS NUMERIC), high = high * CAST(:g AS NUMERIC), "
    "low = low * CAST(:g AS NUMERIC), close_adj = close_adj * CAST(:g AS NUMERIC), "
    "volume = ROUND(CAST(volume AS NUMERIC) / CAST(:g AS NUMERIC)) "
    "WHERE market = :market AND ticker = :ticker AND date < :d"
)


def _scale_history(session: Session, market: str, ticker: str, d: date, g: float) -> int:
    result = session.execute(_ADJUST_SQL, {"g": g, "market": market, "ticker": ticker, "d": d})
    return result.rowcount


def revert_price_basis_event(session: Session, market: str, ticker: str, d: date, factor: float) -> int:
    """자동 적용을 되돌린다(가격 ÷ 계수, 거래량 × 계수). 커밋은 호출자가 한다."""
    return _scale_history(session, market, ticker, d, 1 / factor)


def _record_flag(session: Session, market: str, ev: PriceBasisEvent) -> None:
    existing = session.execute(
        select(CorporateActionFlag.id, CorporateActionFlag.status, CorporateActionFlag.detected_signal)
        .where(CorporateActionFlag.ticker == ev.ticker)
    ).first()
    line = ev.signal_text()

    if existing is not None:
        values = {
            "detected_signal": f"{existing.detected_signal}\n{line}" if existing.detected_signal else line,
        }
        if not ev.is_auto and existing.status == "resolved":
            values["status"] = "pending"
        session.execute(
            update(CorporateActionFlag).where(CorporateActionFlag.id == existing.id).values(**values)
        )
        return

    if ev.kind == KIND_SHARE_BASIS:
        # 병합과 감자는 기준가·주식 수만으로 구분할 수 없다 — 둘 다 merge로 기록한다.
        reason = "split" if ev.factor < 1 else "merge"
        note = "KRX 기준가 자동 소급 보정(분할·병합·감자). 되돌리기: date < flag_date 가격 ÷ factor, 거래량 × factor"
        status = "resolved"
    elif ev.kind == KIND_RIGHTS:
        reason = "new_issuance"
        note = "KRX 기준가 자동 소급 보정(무상·유상증자 권리락). 되돌리기: date < flag_date 가격 ÷ factor, 거래량 × factor"
        status = "resolved"
    elif ev.kind == KIND_OVERRIDE:
        reason = "manual"
        note = "수동 지정 계수로 소급 보정(자동 분류 보류 건). 되돌리기: date < flag_date 가격 ÷ factor, 거래량 × factor"
        status = "resolved"
    else:
        reason = "manual"
        note = "KRX 기준가 변동이 자동 분류 규칙에 맞지 않아 보정 보류 — 수동 검토 필요"
        status = "pending"

    session.add(CorporateActionFlag(
        ticker=ev.ticker, market=market, flag_date=ev.date, reason=reason,
        status=status, detected_signal=line, note=note,
    ))


def apply_price_basis_events(session: Session, market: str, d: date, events: list[PriceBasisEvent]) -> None:
    """
    자동 이벤트는 D 이전 이력을 조정하고, 모든 이벤트를 corporate_action_flag에 기록한다.
    커밋하지 않는다 — 호출자가 D일 행 저장과 함께 한 트랜잭션으로 커밋한다.
    """
    for ev in events:
        if ev.is_auto:
            n = _scale_history(session, market, ev.ticker, d, ev.factor)
            logger.info("%s %s 소급 보정: %s (%d행)", market, ev.ticker, ev.signal_text(), n)
        else:
            logger.warning("%s %s 보정 보류: %s", market, ev.ticker, ev.signal_text())
        _record_flag(session, market, ev)


def report_price_basis_events(market: str, events: list[PriceBasisEvent]) -> None:
    """커밋 이후 Sentry 전송 — 자동 적용은 info, 보류는 warning."""
    try:
        import sentry_sdk
    except Exception:
        return
    for ev in events:
        try:
            if ev.is_auto:
                sentry_sdk.capture_message(
                    f"[{market.upper()}] 가격 소급 보정 자동 적용: {ev.ticker} {ev.signal_text()}",
                    level="info",
                )
            else:
                sentry_sdk.capture_message(
                    f"[{market.upper()}] 가격 기준 변동 보류(랭킹 제외, 수동 검토): {ev.ticker} {ev.signal_text()}",
                    level="warning",
                )
        except Exception:
            pass
