"""
공유 카드 PNG(1200×630) 렌더러.

폰트는 모듈 import 시점에 1회만 로드한다 — 요청마다 OTF(각 ~1.5MB)를 다시 열면
동시 요청 시 메모리 피크가 커진다. 렌더링 자체는 CPU 바운드라 호출부(api/share.py)가
threadpool에서 실행한다. 공유 폰트 객체(FreeType face)는 스레드 안전이 보장되지 않아
렌더링을 Lock으로 직렬화한다(1회 ~12ms라 병목이 되지 않는다).

색상은 프론트 tokens.ts의 DARK 팔레트와 같다(상승 green / 하락 red).
카드 디자인을 바꾸면 Worker의 R2 키 버전(og/v1 → v2)도 함께 올려야 한다 —
그러지 않으면 이미 캐시된 옛 디자인 카드가 계속 서빙된다.
"""

import threading
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from fomobot.services.share import ShareSnapshot

WIDTH, HEIGHT = 1200, 630
PAD = 72
CONTENT_WIDTH = WIDTH - PAD * 2

# tokens.ts DARK. 반투명 토큰(border, blueFill)은 bg 위에 합성한 불투명 값.
BG = (0x0B, 0x0D, 0x12)
TEXT_PRIMARY = (0xE9, 0xED, 0xF5)
TEXT_SUB = (0xC7, 0xCE, 0xDC)
TEXT_MUTED = (0x9A, 0xA5, 0xB8)
TEXT_DIM = (0x7C, 0x86, 0x99)
GREEN = (0x1E, 0xCB, 0x81)
RED = (0xFF, 0x4D, 0x62)
ORANGE = (0xF4, 0xA9, 0x3C)
BLUE_SOFT = (0x7A, 0xA2, 0xFF)
BORDER = (0x1F, 0x20, 0x25)      # rgba(255,255,255,0.08) on BG
CHIP_BG = (0x13, 0x1E, 0x35)     # rgba(62,123,250,0.15) on BG

_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(_FONT_DIR / f"Pretendard-{weight}.otf"), size)


NAME_SIZES = (64, 56, 48)
RETURN_SIZES = (160, 136, 112, 96)

FONT_LOGO = _font("Bold", 34)
FONT_CHIP = _font("Bold", 22)
FONT_NAME = {size: _font("ExtraBold", size) for size in NAME_SIZES}
FONT_META = _font("Regular", 30)
FONT_RETURN = {size: _font("ExtraBold", size) for size in RETURN_SIZES}
FONT_VALUE = _font("Bold", 38)
FONT_MDD = _font("Regular", 30)
FONT_FOOTER = _font("Regular", 24)

_render_lock = threading.Lock()


def round1(v: float) -> Decimal:
    """소수 첫째 자리 반올림. JS toFixed(1)(프론트 fmtPct, Worker 메타 문구)와 같은 규칙 —
    float의 실제 2진 값을 기준으로 하고 정확히 .x5면 0에서 먼 쪽으로 올린다.
    Python 기본 포맷(.1f)은 짝수 쪽으로 반올림해 12.25가 카드엔 12.2, 메타엔 12.3으로
    갈라지므로 쓰지 않는다."""
    return Decimal(v).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def is_flat(v: float) -> bool:
    """반올림 결과가 0.0이면 상승/하락 어느 쪽으로도 표시하지 않는다."""
    return round1(v) == 0


def fmt_pct(v: float) -> str:
    r = round1(v)
    if r == 0:
        return "0.0%"
    return f"{'+' if r > 0 else ''}{r:,.1f}%"


def fmt_money(v: int, currency: str) -> str:
    """앱 백테스트 패널(BacktestPanel.fmtMoney)과 같은 표기 — ₩1,000,000 / $10,000."""
    return f"{'₩' if currency == 'KRW' else '$'}{v:,}"


def _fit_size(
    draw: ImageDraw.ImageDraw, text: str, fonts: dict[int, ImageFont.FreeTypeFont]
) -> ImageFont.FreeTypeFont | None:
    """큰 크기부터 시도해 CONTENT_WIDTH 안에 들어오는 첫 폰트. 전부 넘치면 None."""
    for size in sorted(fonts, reverse=True):
        if draw.textlength(text, font=fonts[size]) <= CONTENT_WIDTH:
            return fonts[size]
    return None


def _fit_name(draw: ImageDraw.ImageDraw, name: str) -> tuple[str, ImageFont.FreeTypeFont]:
    """긴 종목명은 글자 크기를 줄여보고, 그래도 넘치면 말줄임한다."""
    font = _fit_size(draw, name, FONT_NAME)
    if font is not None:
        return name, font
    font = FONT_NAME[NAME_SIZES[-1]]
    text = name
    while text and draw.textlength(text + "…", font=font) > CONTENT_WIDTH:
        text = text[:-1]
    return text.rstrip() + "…", font


def render_card(snap: ShareSnapshot) -> bytes:
    with _render_lock:
        return _render(snap)


def _render(snap: ShareSnapshot) -> bytes:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    if is_flat(snap.return_pct):
        accent = TEXT_MUTED
    else:
        accent = GREEN if snap.return_pct > 0 else RED
    draw.rectangle((0, 0, WIDTH, 6), fill=accent)

    # 상단: 로고 + 시장 칩
    draw.text((PAD, 96), "FomoBot", font=FONT_LOGO, fill=TEXT_PRIMARY, anchor="ls")
    chip_text = snap.market.upper()
    chip_w = draw.textlength(chip_text, font=FONT_CHIP) + 32
    chip_box = (WIDTH - PAD - chip_w, 62, WIDTH - PAD, 106)
    draw.rounded_rectangle(chip_box, radius=10, fill=CHIP_BG)
    draw.text(
        ((chip_box[0] + chip_box[2]) / 2, (chip_box[1] + chip_box[3]) / 2),
        chip_text, font=FONT_CHIP, fill=BLUE_SOFT, anchor="mm",
    )

    # 종목명 / 티커 · 기간
    name, name_font = _fit_name(draw, snap.name)
    draw.text((PAD, 192), name, font=name_font, fill=TEXT_PRIMARY, anchor="ls")
    meta = f"{snap.ticker} · {snap.from_date.isoformat()} ~ {snap.to_date.isoformat()}"
    draw.text((PAD, 242), meta, font=FONT_META, fill=TEXT_MUTED, anchor="ls")

    # 수익률 — 가장 크게. 숫자는 말줄임하면 안 되므로 크기만 줄인다(최소 크기에서
    # 넘치는 값은 사실상 없지만, 그 경우에도 잘라내지 않고 최소 크기로 그린다).
    ret_text = fmt_pct(snap.return_pct)
    ret_font = _fit_size(draw, ret_text, FONT_RETURN) or FONT_RETURN[RETURN_SIZES[-1]]
    draw.text((PAD, 402), ret_text, font=ret_font, fill=accent, anchor="ls")

    # 원금 → 평가액
    head = f"{fmt_money(snap.principal, snap.currency)} → "
    draw.text((PAD, 478), head, font=FONT_VALUE, fill=TEXT_SUB, anchor="ls")
    tail_x = PAD + draw.textlength(head, font=FONT_VALUE)
    draw.text((tail_x, 478), fmt_money(snap.end_value, snap.currency), font=FONT_VALUE, fill=accent, anchor="ls")

    # MDD — 반올림하면 0인 값이 "-0.0%"로 찍히지 않게 정리
    mdd = round1(snap.mdd_pct)
    mdd_text = "0.0" if mdd == 0 else f"{mdd:,.1f}"
    draw.text((PAD, 526), f"기간 중 최대 하락 {mdd_text}%", font=FONT_MDD, fill=ORANGE, anchor="ls")

    # 하단
    draw.line((PAD, 556, WIDTH - PAD, 556), fill=BORDER, width=2)
    footer = f"{snap.to_date.isoformat()} 종가 기준 · 배당 미반영 · fomobot.net"
    draw.text((PAD, 598), footer, font=FONT_FOOTER, fill=TEXT_DIM, anchor="ls")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
