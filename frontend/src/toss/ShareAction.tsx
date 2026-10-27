import { useEffect, useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { TOSS_UI } from '../i18n/strings.toss'
import { shareRoute } from './share'
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
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!failed) return
    const id = setTimeout(() => setFailed(false), 3000)
    return () => clearTimeout(id)
  }, [failed])

  const onClick = () => {
    if (busy) return
    setBusy(true)
    setFailed(false)
    shareRoute(route, asOf, message)
      .catch((e: unknown) => {
        console.error('[ShareAction] 공유 실패', e)
        setFailed(true)
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
      {failed && (
        <div role="status" style={{
          position: 'fixed', left: 16, right: 16, bottom: 'calc(16px + env(safe-area-inset-bottom))', zIndex: 20,
          padding: '12px 16px', borderRadius: 12, background: 'rgba(17,24,39,0.92)', color: '#fff',
          fontSize: 13.5, fontFamily: FONT.sans, textAlign: 'center',
        }}>
          {TOSS_UI.shareFailed}
        </div>
      )}
    </>
  )
}
