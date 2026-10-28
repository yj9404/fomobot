import { useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { TOSS_UI } from '../i18n/strings.toss'
import { shareRoute } from './share'
import { useToast } from './Toast'
import type { Route } from './routes'

interface Props {
  route: Route
  asOf: string
  message: string
  /** compact: 순위 화면 기준일 줄에 붙는 작은 버튼. 기본은 상세 화면의 전체 너비 버튼. */
  compact?: boolean
}

export function ShareAction({ route, asOf, message, compact = false }: Props) {
  const C = useC()
  const [busy, setBusy] = useState(false)
  const [toast, showToast] = useToast()

  const onClick = () => {
    if (busy) return
    setBusy(true)
    shareRoute(route, asOf, message)
      .catch((e: unknown) => {
        console.error('[ShareAction] 공유 실패', e)
        showToast(TOSS_UI.shareFailed)
      })
      .finally(() => setBusy(false))
  }

  const button: React.CSSProperties = compact
    ? {
        marginLeft: 'auto', padding: '8px 14px', minHeight: 40, borderRadius: 9, border: 'none',
        background: C.surfaceAlt, color: C.textSub, fontSize: 12.5, fontWeight: 600,
      }
    : {
        width: '100%', padding: '14px 0', borderRadius: 12, border: 'none',
        background: 'rgba(62,123,250,0.12)', color: C.blueSoft, fontSize: 15, fontWeight: 700,
      }

  return (
    <>
      <button onClick={onClick} disabled={busy} style={{ ...button, fontFamily: FONT.sans, cursor: 'pointer', opacity: busy ? 0.6 : 1 }}>
        {TOSS_UI.share}
      </button>
      {toast}
    </>
  )
}
