import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
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

function Segment<V extends string>({ options, value, onChange }: {
  options: { value: V; label: string }[]
  value: V
  onChange: (v: V) => void
}) {
  const C = useC()
  return (
    <div style={{ padding: '0 16px 8px' }}>
      <div style={{ display: 'flex', gap: 4, background: C.surfaceAlt, border: `1px solid ${C.borderSub}`, borderRadius: 12, padding: 4 }}>
        {options.map((o) => (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            style={{
              flex: 1, textAlign: 'center', padding: '10px 0', border: 'none', borderRadius: 9,
              fontSize: 14, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer',
              background: value === o.value ? 'linear-gradient(135deg,#3E7BFA,#2F66E0)' : 'transparent',
              color: value === o.value ? '#fff' : C.textMuted,
            }}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}

/**
 * 토스 미니앱용 컨트롤 영역. 로고·언어/테마 토글·뒤로가기는 두지 않는다 —
 * 상단 내비게이션 바는 앱인토스 SDK가 제공하므로 겹치면 안 된다.
 * 시장과 정렬은 같은 비중의 주요 선택지라 둘 다 세그먼트로 두고 고정(sticky)하며, 기간·시총 칩은 스크롤된다.
 */
export function TossHeader({ market, periodIdx, capTier, order, t, onMarket, onPeriod, onCapTier, onOrder }: Props) {
  const C = useC()

  const chip = (active: boolean): React.CSSProperties => ({
    padding: '8px 13px', borderRadius: 10, border: 'none', flexShrink: 0, whiteSpace: 'nowrap',
    fontSize: 13, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer',
    background: active ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
    color: active ? C.blueSoft : C.textMuted,
  })
  const scrollRow: React.CSSProperties = { display: 'flex', gap: 6, padding: '0 16px', overflowX: 'auto', scrollbarWidth: 'none' }

  return (
    <>
      {/* 시장·정렬은 스크롤해도 남는다(sticky). 호출하는 쪽의 세로 flex 컨테이너가 스크롤 영역이어야 한다. */}
      <div style={{ position: 'sticky', top: 0, zIndex: 10, background: C.surface, fontFamily: FONT.sans, paddingTop: 12, borderBottom: `1px solid ${C.borderFaint}` }}>
        <Segment
          options={[{ value: 'kospi' as Market, label: 'KOSPI' }, { value: 'nasdaq' as Market, label: 'NASDAQ' }]}
          value={market}
          onChange={onMarket}
        />
        <Segment
          options={[{ value: 'desc' as OrderDir, label: t.orderRise }, { value: 'asc' as OrderDir, label: t.orderFall }]}
          value={order}
          onChange={onOrder}
        />
      </div>

      <div style={{ width: '100%', fontFamily: FONT.sans, background: C.surface, paddingTop: 10 }}>
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
        </div>

        <div style={{ margin: '0 16px 10px', fontSize: 11.5, color: C.textDim, lineHeight: 1.4 }}>
          {t.disclaimer}
        </div>
      </div>
    </>
  )
}
