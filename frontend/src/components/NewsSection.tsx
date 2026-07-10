import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import type { NewsArticle } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  show: boolean
  status: 'idle' | 'loading' | 'ok' | 'error'
  articles: NewsArticle[]
  t: Strings
}

/**
 * 펼침 영역 맨 끝에 붙는 뉴스 블록 (주식 BacktestPanel / 부동산 ReResultArea 공용).
 *
 * 2단계 지연 로딩 원칙 준수: show=false(has_news 아님), status가 idle/error,
 * 혹은 ok인데 기사가 0건이면 아무것도 렌더링하지 않는다("관련 기사 없음"
 * 같은 문구도 넣지 않는다). 기사 제목/링크/날짜는 원문 그대로 표시하고
 * 요약·해석 문구를 덧붙이지 않는다.
 */
export function NewsSection({ show, status, articles, t }: Props) {
  const C = useC()

  if (!show) return null
  if (status === 'idle' || status === 'error') return null
  if (status === 'ok' && articles.length === 0) return null

  if (status === 'loading') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 2 }}>
        <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(62,123,250,0.25)', borderTopColor: C.blue, animation: 'fb-spin .8s linear infinite' }} />
        <span style={{ fontSize: 11.5, color: C.textDim }}>{t.newsLoading}</span>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: C.textMuted, letterSpacing: '0.02em' }}>
        {t.newsTitle}
      </span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {articles.map((a) => (
          <a
            key={a.link}
            href={a.link}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'block',
              textDecoration: 'none',
              padding: '8px 10px',
              borderRadius: 8,
              background: C.surfaceAlt,
              border: `1px solid ${C.borderFaint}`,
            }}
          >
            <div style={{
              fontSize: 12.5, fontWeight: 600, color: C.blueSoft, lineHeight: 1.4,
              textDecoration: 'underline', textDecorationColor: 'rgba(122,162,255,0.35)',
            }}>
              {a.title}
            </div>
            <div style={{ fontSize: 10.5, color: C.textDim, fontFamily: FONT.mono, marginTop: 3 }}>
              {a.published_at}
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}
