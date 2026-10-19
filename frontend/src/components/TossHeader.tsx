import { useC, useTheme } from '../ThemeContext'
import { FONT, DECLINE_ACCENT_LIGHT } from '../tokens'
import { PERIODS, CAP_TIERS } from '../types'
import type { CapTier, Market, OrderDir } from '../types'
import type { CommonStrings } from '../i18n/strings'

interface Props {
  market: Market
  periodIdx: number
  capTier: CapTier
  order: OrderDir
  t: CommonStrings
  onMarket: (m: Market) => void
  onPeriod: (i: number) => void
  onCapTier: (c: CapTier) => void
  onOrder: (o: OrderDir) => void
}

/**
 * 토스 미니앱용 컨트롤 영역. 로고·언어/테마 토글·뒤로가기는 두지 않는다 —
 * 상단 내비게이션 바는 앱인토스 SDK가 제공하므로 겹치면 안 된다.
 */
export function TossHeader({ market, periodIdx, capTier, order, t, onMarket, onPeriod, onCapTier, onOrder }: Props) {
  const C = useC()
  const { atmosphereMode } = useTheme()
  const da = DECLINE_ACCENT_LIGHT
  const isFall = atmosphereMode === 'fall'

  const chip = (active: boolean): React.CSSProperties => ({
    padding: '8px 13px', borderRadius: 10, border: 'none', flexShrink: 0, whiteSpace: 'nowrap',
    fontSize: 13, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer',
    background: active ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
    color: active ? C.blueSoft : C.textMuted,
  })
  const scrollRow: React.CSSProperties = { display: 'flex', gap: 6, padding: '0 16px', overflowX: 'auto', scrollbarWidth: 'none' }

  return (
    <div style={{ width: '100%', fontFamily: FONT.sans, background: C.surface, position: 'sticky', top: 0, zIndex: 10, paddingTop: 12 }}>
      <div style={{ padding: '0 16px 10px' }}>
        <div style={{ display: 'flex', gap: 4, background: C.surfaceAlt, border: `1px solid ${C.borderSub}`, borderRadius: 12, padding: 4 }}>
          {(['kospi', 'nasdaq'] as Market[]).map((m) => (
            <button
              key={m}
              onClick={() => onMarket(m)}
              style={{
                flex: 1, textAlign: 'center', padding: '10px 0', border: 'none', borderRadius: 9,
                fontSize: 14, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer',
                background: market === m ? 'linear-gradient(135deg,#3E7BFA,#2F66E0)' : 'transparent',
                color: market === m ? '#fff' : C.textMuted,
              }}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div style={{ ...scrollRow, paddingBottom: 8 }}>
        {PERIODS.map((p, i) => (
          <button key={p.value} onClick={() => onPeriod(i)} style={chip(periodIdx === i)}>
            {p.label.ko}
          </button>
        ))}
      </div>

      <div style={{ ...scrollRow, paddingBottom: 10 }}>
        {CAP_TIERS.map((c) => (
          <button key={c.value} onClick={() => onCapTier(c.value)} style={chip(capTier === c.value)}>
            {c.label.ko}
          </button>
        ))}
        <div style={{ width: 1, height: 20, background: C.borderSub, flexShrink: 0, alignSelf: 'center' }} />
        {(['desc', 'asc'] as OrderDir[]).map((o) => {
          const useFall = order === o && o === 'asc' && isFall
          return (
            <button
              key={o}
              onClick={() => onOrder(o)}
              style={{
                ...chip(order === o),
                background: order === o ? (useFall ? da.activeBg : 'rgba(62,123,250,0.14)') : C.surfaceAlt,
                color: order === o ? (useFall ? da.activeText : C.blueSoft) : C.textMuted,
              }}
            >
              {o === 'desc' ? t.orderRise : t.orderFall}
            </button>
          )
        })}
      </div>

      <div style={{ margin: '0 16px 10px', fontSize: 11.5, color: C.textDim, lineHeight: 1.4 }}>
        {t.disclaimer}
      </div>
    </div>
  )
}
