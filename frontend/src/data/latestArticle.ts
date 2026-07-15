export interface LatestArticle {
  href: string
  ko: { title: string; summary: string }
  en: { title: string; summary: string }
}

// 새 글을 발행하면 이 객체 하나만 교체한다 (컴포넌트/구조 변경 불필요).
// 메인 화면 랭킹 리스트 하단의 "읽을거리" 카드(ArticleTeaser)에 그대로 노출된다.
export const LATEST_ARTICLE: LatestArticle = {
  href: '/adjusted-price-trap.html',
  ko: {
    title: '같은 이름의 다른 물건 — 수정주가라는 함정',
    summary: 'pykrx는 배당을 빼고 yfinance는 넣습니다. 우리 방법론 문서가 틀렸던 이유',
  },
  en: {
    title: 'Same Name, Different Thing — The Adjusted-Price Trap',
    summary: 'pykrx excludes dividends, yfinance includes them — why our own docs were wrong',
  },
}
