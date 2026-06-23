import { C, FONT } from '../tokens'
import type { Strings } from '../i18n/strings'

export function ErrorState({ t, errorMsg, onRetry }: { t: Strings; errorMsg: string; onRetry: () => void }) {
  return (
    <div style={{ borderTop: `1px solid ${C.borderSub}`, padding: '56px 28px 60px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 13, fontFamily: FONT.sans }}>
      <div style={{ width: 62, height: 62, borderRadius: '50%', background: 'rgba(255,77,98,0.08)', border: '1px solid rgba(255,77,98,0.22)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 30, fontWeight: 800, color: C.red, lineHeight: 1 }}>
        !
      </div>
      <div style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary }}>{t.errorTitle}</div>
      <div style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.5, maxWidth: 240 }}>
        {t.errorSub}{' '}
        {errorMsg && <span style={{ fontFamily: FONT.mono, color: C.textDim, fontSize: 11 }}>{errorMsg}</span>}
      </div>
      <button
        onClick={onRetry}
        style={{ marginTop: 6, padding: '10px 22px', border: 'none', borderRadius: 11, background: 'linear-gradient(135deg,#3E7BFA,#2F66E0)', color: '#fff', fontSize: 13, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer', boxShadow: '0 4px 14px rgba(62,123,250,0.35)' }}
      >
        {t.retry}
      </button>
    </div>
  )
}
