"""
토스판 뉴스 표시용 가공 — 링크 검사, 언론사 이름, 권유형 제목 제외.

저장(stock_news)과 웹 응답은 그대로 두고 토스 응답에만 적용한다.
제목 필터를 클라이언트가 아닌 서버에 두는 이유: 단어 목록이 토스 번들에 들어가면
금지 토큰 가드(frontend/scripts/check-toss-bundle.mjs --strict)에 걸린다.
"""

import re
from urllib.parse import urlparse

# 앱인토스 정책상 종목 추천·투자 자문으로 읽힐 수 있는 권유·전망형 표현.
# "급등/급락/상한가" 같은 가격 변동 서술은 사실 보도라 제외하지 않는다(수집 대상이 랭킹 종목이라
# 이걸 막으면 기사가 거의 남지 않는다). "외국인 순매수" 같은 사실 기사도 일부 빠지지만 보수적으로 둔다.
ADVICE_TITLE_RE = re.compile(r"매수|매도|추천|목표가|목표주가|유망|사야|담아|리딩방|수익\s?보장")

# 원문 도메인 → 언론사 이름. 하위 도메인(m., news. 등)도 매칭되며, 더 긴(구체적인) 도메인이 우선한다.
# 없는 도메인은 호스트명을 그대로 표시하므로 빠짐없이 채울 필요는 없다.
PRESS_BY_DOMAIN: dict[str, str] = {
    "news.naver.com": "네이버뉴스",
    "yna.co.kr": "연합뉴스",
    "yonhapnewstv.co.kr": "연합뉴스TV",
    "newsis.com": "뉴시스",
    "news1.kr": "뉴스1",
    "hankyung.com": "한국경제",
    "wowtv.co.kr": "한국경제TV",
    "mk.co.kr": "매일경제",
    "mbn.co.kr": "MBN",
    "sedaily.com": "서울경제",
    "sentv.co.kr": "서울경제TV",
    "edaily.co.kr": "이데일리",
    "mt.co.kr": "머니투데이",
    "fnnews.com": "파이낸셜뉴스",
    "asiae.co.kr": "아시아경제",
    "heraldcorp.com": "헤럴드경제",
    "etoday.co.kr": "이투데이",
    "ajunews.com": "아주경제",
    "newspim.com": "뉴스핌",
    "inews24.com": "아이뉴스24",
    "dt.co.kr": "디지털타임스",
    "etnews.com": "전자신문",
    "zdnet.co.kr": "지디넷코리아",
    "thebell.co.kr": "더벨",
    "bizwatch.co.kr": "비즈니스워치",
    "businesspost.co.kr": "비즈니스포스트",
    "ebn.co.kr": "EBN",
    "dailian.co.kr": "데일리안",
    "chosun.com": "조선일보",
    "biz.chosun.com": "조선비즈",
    "joongang.co.kr": "중앙일보",
    "donga.com": "동아일보",
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "hankookilbo.com": "한국일보",
    "seoul.co.kr": "서울신문",
    "kmib.co.kr": "국민일보",
    "munhwa.com": "문화일보",
    "segye.com": "세계일보",
    "nocutnews.co.kr": "노컷뉴스",
    "ohmynews.com": "오마이뉴스",
    "kukinews.com": "쿠키뉴스",
    "ytn.co.kr": "YTN",
    "kbs.co.kr": "KBS",
    "imbc.com": "MBC",
    "sbs.co.kr": "SBS",
    "biz.sbs.co.kr": "SBS Biz",
    "jtbc.co.kr": "JTBC",
}

_DOMAINS_LONGEST_FIRST = sorted(PRESS_BY_DOMAIN, key=len, reverse=True)


def safe_web_host(link: str) -> str | None:
    """http/https 링크면 소문자 호스트명을, 아니면(javascript:, intent:, 딥링크 등) None을 반환한다."""
    try:
        parsed = urlparse(link)
    except ValueError:
        return None
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        return None
    return parsed.hostname.lower()


def press_name(host: str) -> str:
    """호스트명에서 언론사 이름을 찾는다. 매핑에 없으면 www./m. 를 뗀 호스트명을 그대로 쓴다."""
    for domain in _DOMAINS_LONGEST_FIRST:
        if host == domain or host.endswith("." + domain):
            return PRESS_BY_DOMAIN[domain]
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            return host[len(prefix):]
    return host


def is_advice_title(title: str) -> bool:
    return ADVICE_TITLE_RE.search(title) is not None
