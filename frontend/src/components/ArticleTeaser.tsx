import { useC } from '../ThemeContext'
import ARTICLES from '../data/articles.json'
import type { Lang } from '../types'

/**
 * 랭킹 리스트 하단, 광고 슬롯 위에 노출하는 "읽을거리" 카드.
 * 링크만 있는 배너가 아니라 제목/요약 텍스트를 실제로 렌더해
 * "광고가 뜨는 화면에 콘텐츠가 있다"는 근거가 되도록 한다.
 *
 * 노출할 글은 articles.json 전체에서 매 페이지 로드마다 무작위로 하나 뽑는다
 * (모듈 로드 시 한 번 결정 → 같은 세션 안에서는 고정, 새로고침하면 다시 추첨).
 * 데스크톱·모바일 레이아웃 모두 이 컴포넌트를 그대로 쓴다.
 * 글 본문은 한국어 전용이라 EN 모드에서도 제목/요약은 한국어를 그대로 노출한다.
 */
const ARTICLE = ARTICLES[Math.floor(Math.random() * ARTICLES.length)]!

export function ArticleTeaser({ lang, style }: { lang: Lang; style?: React.CSSProperties }) {
  const C = useC()
  return (
    <a
      href={`/${ARTICLE.slug}.html`}
      style={{
        display: 'block',
        margin: '16px 20px',
        padding: '14px 16px',
        borderRadius: 12,
        border: `1px solid ${C.borderSub}`,
        background: C.surfaceAlt,
        textDecoration: 'none',
        ...style,
      }}
    >
      <div style={{
        fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
        color: C.blueSoft, marginBottom: 4,
      }}>
        {lang === 'ko' ? '읽을거리' : 'Articles'}
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary }}>
        {ARTICLE.title} →
      </div>
      <div style={{ fontSize: 11, color: C.textDim, marginTop: 2 }}>
        {ARTICLE.teaser}
      </div>
    </a>
  )
}
