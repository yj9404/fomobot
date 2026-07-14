export interface LatestArticle {
  href: string
  ko: { title: string; summary: string }
  en: { title: string; summary: string }
}

// 새 글을 발행하면 이 객체 하나만 교체한다 (컴포넌트/구조 변경 불필요).
// 메인 화면 랭킹 리스트 하단의 "읽을거리" 카드(ArticleTeaser)에 그대로 노출된다.
export const LATEST_ARTICLE: LatestArticle = {
  href: '/five-year-winner.html',
  ko: {
    title: '5년 수익률 1위를 들고 있으려면',
    summary: '수익률 뒤에 숨은 -30%대 하락 네 번, 그 이야기',
  },
  en: {
    title: 'What It Takes to Hold the 5-Year Winner',
    summary: 'Behind the return: four drawdowns past -30%',
  },
}
