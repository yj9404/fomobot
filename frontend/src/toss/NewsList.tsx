import { useRef } from 'react'
import { Device } from '@apps-in-toss/web-framework'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { TOSS_UI } from '../i18n/strings.toss'
import type { TossNewsArticle } from './api'
import { daysSince, todayKst } from './detail'
import { useToast } from './Toast'

// 연타로 브라우저가 여러 번 열리지 않게 이 시간 안의 재탭은 무시한다.
// openURL이 끝나길 기다리는 방식은 브리지가 응답하지 않으면 영영 막히므로 시간으로 막는다.
const TAP_GUARD_MS = 1000

/**
 * 종목 상세의 관련 뉴스. 제목·언론사·발행일(상대 일수)만 보여주고 본문 요약·썸네일은 두지 않는다.
 * 원문은 Device.openURL로 기기 브라우저에서 연다 — 웹뷰 안 새 창·이동·임베드는 쓰지 않는다.
 * 아래의 굵은 띠는 안내 문구·배너 광고와 목록을 떼어 놓아 광고로 오인되지 않게 한다.
 */
export function NewsList({ articles }: { articles: TossNewsArticle[] }) {
  const C = useC()
  const [toast, showToast] = useToast()
  const lastTap = useRef(0)

  if (articles.length === 0) return null
  const today = todayKst()

  const open = (url: string) => {
    const now = Date.now()
    if (now - lastTap.current < TAP_GUARD_MS) return
    lastTap.current = now
    const fail = (e: unknown) => {
      console.error('[NewsList] 기사 열기 실패', e)
      showToast(TOSS_UI.newsOpenFailed)
    }
    // 서버가 http/https만 주지만, 다른 스킴이 openURL로 앱·딥링크를 열지 않게 한 번 더 막는다.
    if (!/^https?:\/\//i.test(url)) return fail(new Error(`unsupported url: ${url}`))
    // 토스 밖(일반 브라우저)에서는 동기 예외가 날 수 있어 Promise 안에서 부른다.
    Promise.resolve().then(() => Device.openURL(url)).catch(fail)
  }

  return (
    <>
      <div style={{ padding: '28px 16px 4px', fontSize: 14, fontWeight: 700, color: C.textPrimary }}>{TOSS_UI.news}</div>
      {articles.map((a) => (
        <button
          key={a.url}
          onClick={() => open(a.url)}
          style={{
            display: 'block', width: '100%', minHeight: 56, padding: '12px 16px', textAlign: 'left',
            background: 'none', border: 'none', borderBottom: `1px solid ${C.borderFaint}`,
            fontFamily: FONT.sans, cursor: 'pointer',
          }}
        >
          <div style={{
            fontSize: 14, color: C.textSub, lineHeight: 1.45, wordBreak: 'keep-all',
            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
          }}>
            {a.title}
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: C.textDim }}>
            {a.source} · {TOSS_UI.daysAgo(daysSince(a.published_at, today))}
          </div>
        </button>
      ))}
      <div style={{ height: 8, marginTop: 16, background: C.surfaceAlt }} />
      {toast}
    </>
  )
}
