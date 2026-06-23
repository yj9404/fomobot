import { C, FONT } from '../tokens'
import type { Strings } from '../i18n/strings'

const shimmer: React.CSSProperties = {
  background: 'linear-gradient(90deg,#161B26 25%,#222B3A 50%,#161B26 75%)',
  backgroundSize: '400px 100%',
  animation: 'fb-shimmer 1.4s infinite linear',
  borderRadius: 5,
}

function SkeletonRow({ w1, w2 }: { w1: string; w2: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '14px 16px', borderBottom: `1px solid ${C.borderFaint}` }}>
      <div style={{ ...shimmer, width: 18, height: 12, borderRadius: 4, flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div style={{ ...shimmer, width: w1, height: 13 }} />
        <div style={{ ...shimmer, width: w2, height: 9, marginTop: 8 }} />
      </div>
      <div style={{ ...shimmer, width: 54, height: 18, flexShrink: 0 }} />
    </div>
  )
}

export function SkeletonList({ t }: { t: Strings }) {
  return (
    <div style={{ borderTop: `1px solid ${C.borderSub}` }}>
      <SkeletonRow w1="60%" w2="42%" />
      <SkeletonRow w1="52%" w2="38%" />
      <SkeletonRow w1="66%" w2="44%" />
      <SkeletonRow w1="48%" w2="40%" />
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '26px 16px' }}>
        <div style={{ width: 20, height: 20, borderRadius: '50%', border: '2px solid rgba(62,123,250,0.25)', borderTopColor: C.blue, animation: 'fb-spin .8s linear infinite' }} />
        <div style={{ fontSize: 13, fontWeight: 600, color: C.textSub, fontFamily: FONT.sans }}>{t.loading}</div>
        <div style={{ fontSize: 11.5, color: C.textDim, fontFamily: FONT.sans }}>{t.loadingSub}</div>
      </div>
    </div>
  )
}
