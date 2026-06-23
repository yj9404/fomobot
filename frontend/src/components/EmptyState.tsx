import { C, FONT } from '../tokens'
import type { Strings } from '../i18n/strings'

export function EmptyState({ t, onRetry }: { t: Strings; onRetry: () => void }) {
  return (
    <div style={{ borderTop: `1px solid ${C.borderSub}`, padding: '56px 28px 60px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 13, fontFamily: FONT.sans }}>
      <div style={{ width: 62, height: 62, borderRadius: 18, background: '#11151D', border: '1px solid rgba(255,255,255,0.07)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg width="28" height="28" viewBox="0 0 28 28">
          <line x1="5" y1="14" x2="23" y2="14" stroke={C.textDim} strokeWidth="2.4" strokeLinecap="round" />
        </svg>
      </div>
      <div style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary }}>{t.empty}</div>
      <div style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.5, maxWidth: 240 }}>{t.emptySub}</div>
      <button
        onClick={onRetry}
        style={{ marginTop: 6, padding: '10px 20px', border: '1px solid rgba(255,255,255,0.13)', borderRadius: 11, background: 'transparent', color: C.textSub, fontSize: 13, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer' }}
      >
        {t.emptyBtn}
      </button>
    </div>
  )
}
