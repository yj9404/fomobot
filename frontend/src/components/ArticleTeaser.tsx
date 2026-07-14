import { useC } from '../ThemeContext'
import { LATEST_ARTICLE } from '../data/latestArticle'
import type { Lang } from '../types'

/**
 * 랭킹 리스트 하단, 광고 슬롯 위에 노출하는 최신 글 카드.
 * 링크만 있는 배너가 아니라 제목/요약 텍스트를 실제로 렌더해
 * "광고가 뜨는 화면에 콘텐츠가 있다"는 근거가 되도록 한다.
 */
export function ArticleTeaser({ lang, style }: { lang: Lang; style?: React.CSSProperties }) {
  const C = useC()
  const copy = LATEST_ARTICLE[lang]
  return (
    <a
      href={LATEST_ARTICLE.href}
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
        {copy.title} →
      </div>
      <div style={{ fontSize: 11, color: C.textDim, marginTop: 2 }}>
        {copy.summary}
      </div>
    </a>
  )
}
