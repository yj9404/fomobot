"""
토스 미니앱 공유 카드 PNG(1200×600) 렌더러.

웹 카드(og_card.py)와 따로 둔 이유:
  - 토스 OG 규격은 1200×600이다(웹은 1200×630).
  - 웹 카드는 원금 → 평가액(매수 시나리오)과 웹 도메인을 담는다. 토스 카드는 시세만 담고
    매수 시점·수익금·웹 도메인을 연상시키는 문구를 넣지 않는다.
  - 토스 화면과 같은 라이트 테마, 국내 관례 색(상승 빨강 / 하락 파랑 — frontend tossColors.ts).

순위 카드는 조건(시장·기간·시총·정렬)과 기준일만 담는다 — 특정 종목명을 이미지로
퍼뜨리면 종목 홍보로 읽힐 수 있어서다.

폰트 객체와 반올림 규칙은 og_card.py의 것을 그대로 쓴다. 공유 폰트 객체가 스레드 안전하지
않아 렌더링은 og_card와 같은 Lock으로 직렬화한다.
"""

from datetime import date, timedelta
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from fomobot.services.og_card import _font, _render_lock, fmt_pct, is_flat
from fomobot.services.stock_detail import StockDetail

WIDTH, HEIGHT = 1200, 600
PAD = 72
CONTENT_WIDTH = WIDTH - PAD * 2

# frontend tokens.ts LIGHT / tossColors.ts. 반투명 토큰은 흰 배경 위에 합성한 불투명 값.
BG = (0xFF, 0xFF, 0xFF)
TEXT_PRIMARY = (0x11, 0x18, 0x27)
TEXT_MUTED = (0x6B, 0x72, 0x80)
TEXT_DIM = (0x9C, 0xA3, 0xAF)
BRAND = (0x3E, 0x7B, 0xFA)
CHIP_BG = (0xE8, 0xEF, 0xFE)      # rgba(62,123,250,0.12) on white
BORDER = (0xF2, 0xF2, 0xF2)       # rgba(0,0,0,0.05) on white
KR_UP = (0xF0, 0x44, 0x52)
KR_DOWN = (0x31, 0x82, 0xF6)

DISCLAIMER = "투자 권유가 아니에요. 지난 시세를 보여드려요"

# frontend types.ts PERIODS / CAP_TIERS 라벨, strings.ts orderRise/orderFall과 같은 말.
PERIOD_LABEL = {"1d": "전일", "7d": "7일", "30d": "30일", "90d": "90일", "365d": "1년", "1825d": "5년"}
CAP_LABEL = {"all": "전체", "small": "소형", "mid": "중형", "large": "대형"}
ORDER_LABEL = {"desc": "상승률", "asc": "하락률"}

# frontend toss/routes.ts CHART_PERIODS / DEFAULT_CHART — 상세 차트 구간 탭(1일 제외).
CHART_PERIODS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365, "1825d": 1825}
DEFAULT_CHART = "365d"

NAME_SIZES = (64, 56, 48)
PRICE_SIZES = (96, 80, 64)

FONT_LOGO = _font("Bold", 34)
FONT_CHIP = _font("Bold", 22)
FONT_NAME = {size: _font("ExtraBold", size) for size in NAME_SIZES}
FONT_META = _font("Regular", 30)
FONT_PRICE = {size: _font("ExtraBold", size) for size in PRICE_SIZES}
FONT_CHANGE = _font("Bold", 38)
FONT_LABEL = _font("Regular", 24)
FONT_TITLE = _font("ExtraBold", 72)
FONT_COND = _font("Bold", 30)
FONT_FOOTER = _font("Regular", 24)

# 종목 카드 오른쪽 차트 영역
CHART_BOX = (700, 300, WIDTH - PAD, 470)
PRICE_MAX_WIDTH = CHART_BOX[0] - PAD - 40


def change_color(pct: float) -> tuple[int, int, int]:
    if is_flat(pct):
        return TEXT_MUTED
    return KR_UP if pct > 0 else KR_DOWN


def fmt_price(value: float, market: str) -> str:
    """frontend format.ts fmtPrice와 같은 표기 — 75,000원 / $190.12."""
    if market == "kospi":
        return f"{round(value):,}원"
    return f"${value:,.2f}"


def _fit(
    draw: ImageDraw.ImageDraw, text: str, fonts: dict[int, ImageFont.FreeTypeFont], max_width: float
) -> ImageFont.FreeTypeFont:
    """큰 크기부터 max_width 안에 들어오는 첫 폰트. 전부 넘치면 가장 작은 크기."""
    for size in sorted(fonts, reverse=True):
        if draw.textlength(text, font=fonts[size]) <= max_width:
            return fonts[size]
    return fonts[min(fonts)]


def _fit_name(draw: ImageDraw.ImageDraw, name: str, max_width: float) -> tuple[str, ImageFont.FreeTypeFont]:
    font = _fit(draw, name, FONT_NAME, max_width)
    if draw.textlength(name, font=font) <= max_width:
        return name, font
    text = name
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text.rstrip() + "…", font


def _header(draw: ImageDraw.ImageDraw, market: str | None) -> None:
    draw.rectangle((0, 0, WIDTH, 6), fill=BRAND)
    draw.text((PAD, 96), "FomoBot", font=FONT_LOGO, fill=TEXT_PRIMARY, anchor="ls")
    if market is None:
        return
    chip_text = market.upper()
    chip_w = draw.textlength(chip_text, font=FONT_CHIP) + 32
    chip_box = (WIDTH - PAD - chip_w, 62, WIDTH - PAD, 106)
    draw.rounded_rectangle(chip_box, radius=10, fill=CHIP_BG)
    draw.text(
        ((chip_box[0] + chip_box[2]) / 2, (chip_box[1] + chip_box[3]) / 2),
        chip_text, font=FONT_CHIP, fill=BRAND, anchor="mm",
    )


def _footer(draw: ImageDraw.ImageDraw, text: str) -> None:
    draw.line((PAD, 516, WIDTH - PAD, 516), fill=BORDER, width=2)
    draw.text((PAD, 562), text, font=FONT_FOOTER, fill=TEXT_DIM, anchor="ls")


def _chart(draw: ImageDraw.ImageDraw, points: list[tuple[date, float]], chart: str) -> None:
    """최근 구간 종가 선. 축·날짜 라벨 없이 모양만 — 특정 날짜 가격을 짚지 않는다."""
    if len(points) < 2:
        return
    x0, y0, x1, y1 = CHART_BOX
    prices = [p for _, p in points]
    lo, hi = min(prices), max(prices)
    span = hi - lo or 1.0
    color = change_color((prices[-1] / prices[0] - 1) * 100) if prices[0] > 0 else TEXT_MUTED
    step = (x1 - x0) / (len(prices) - 1)
    xy = [(x0 + i * step, y1 - (p - lo) / span * (y1 - y0)) for i, p in enumerate(prices)]
    draw.text((x0, y0 - 18), f"최근 {PERIOD_LABEL[chart]}", font=FONT_LABEL, fill=TEXT_DIM, anchor="ls")
    draw.line(xy, fill=color, width=4, joint="curve")


def render_toss_stock_card(detail: StockDetail, chart: str = DEFAULT_CHART) -> bytes:
    with _render_lock:
        return _render_stock(detail, chart)


def _render_stock(d: StockDetail, chart: str) -> bytes:
    if d.status != "ok" or d.close is None or d.as_of is None:
        raise ValueError("시세가 없는 종목은 카드를 만들 수 없습니다.")

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _header(draw, d.market)

    name, name_font = _fit_name(draw, d.name, CONTENT_WIDTH)
    draw.text((PAD, 192), name, font=name_font, fill=TEXT_PRIMARY, anchor="ls")
    # 기준일은 하단에 있으므로, 거래정지 등으로 마지막 거래일이 기준일과 다를 때만 따로 적는다.
    meta = d.ticker
    if d.close_date is not None and d.close_date != d.as_of:
        meta += f" · 마지막 거래일 {d.close_date.isoformat()}"
    draw.text((PAD, 242), meta, font=FONT_META, fill=TEXT_MUTED, anchor="ls")

    price_text = fmt_price(d.close, d.market)
    draw.text(
        (PAD, 372), price_text, font=_fit(draw, price_text, FONT_PRICE, PRICE_MAX_WIDTH),
        fill=TEXT_PRIMARY, anchor="ls",
    )
    day = d.changes.get("1d")
    if day is not None:
        head = "전일 대비 "
        draw.text((PAD, 440), head, font=FONT_CHANGE, fill=TEXT_MUTED, anchor="ls")
        draw.text(
            (PAD + draw.textlength(head, font=FONT_CHANGE), 440),
            fmt_pct(day.change_pct), font=FONT_CHANGE, fill=change_color(day.change_pct), anchor="ls",
        )

    chart_start = d.as_of - timedelta(days=CHART_PERIODS[chart])
    _chart(draw, [r for r in d.series if r[0] >= chart_start], chart)

    _footer(draw, f"{d.as_of.isoformat()} 종가 기준 · {DISCLAIMER}")

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_toss_rankings_card(market: str, period: str, cap_tier: str, order: str, as_of: date) -> bytes:
    with _render_lock:
        return _render_rankings(market, period, cap_tier, order, as_of)


def _render_rankings(market: str, period: str, cap_tier: str, order: str, as_of: date) -> bytes:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    # 시장은 조건 칩에 들어가므로 머리의 시장 칩은 생략한다.
    _header(draw, None)

    draw.text((PAD, 250), "기간별 등락률 순위", font=FONT_TITLE, fill=TEXT_PRIMARY, anchor="ls")

    # 조건 칩: 시장 · 기간 · 시총 · 정렬 — 화면에서 고른 상태 그대로
    x = PAD
    for text in (market.upper(), PERIOD_LABEL[period], f"시총 {CAP_LABEL[cap_tier]}", f"{ORDER_LABEL[order]} 순"):
        w = draw.textlength(text, font=FONT_COND) + 40
        draw.rounded_rectangle((x, 300, x + w, 356), radius=12, fill=CHIP_BG)
        draw.text((x + w / 2, 328), text, font=FONT_COND, fill=BRAND, anchor="mm")
        x += w + 12

    draw.text((PAD, 440), f"{as_of.isoformat()} 종가 기준", font=FONT_META, fill=TEXT_MUTED, anchor="ls")
    _footer(draw, DISCLAIMER)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
