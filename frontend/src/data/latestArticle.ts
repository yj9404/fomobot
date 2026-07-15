export interface LatestArticle {
  href: string
  ko: { title: string; summary: string }
  en: { title: string; summary: string }
}

// 새 글을 발행하면 이 객체 하나만 교체한다 (컴포넌트/구조 변경 불필요).
// 메인 화면 랭킹 리스트 하단의 "읽을거리" 카드(ArticleTeaser)에 그대로 노출된다.
export const LATEST_ARTICLE: LatestArticle = {
  href: '/catching-the-knife.html',
  ko: {
    title: '떨어진 걸 주우면 반등하나',
    summary: '급락 상위10 역발상 매수 검증',
  },
  en: {
    title: 'Does Catching a Falling Knife Ever Pay Off',
    summary: 'Testing the contrarian buy-the-dip strategy — NASDAQ lost to random 9 times out of 10',
  },
}
