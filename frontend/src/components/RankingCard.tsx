import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { BacktestPanel } from './BacktestPanel'
import type { RankingItem, Market } from '../types'
import type { Strings } from '../i18n/strings'

interface BtEntry {
  status: 'idle' | 'loading' | 'ok' | 'error'
  item: import('../types').BacktestItem | null
}

interface Props {
  item: RankingItem
  open: boolean
  market: Market
  days: number
  bt: BtEntry
  t: Strings
  onToggle: () => void
}

function fmtPct(n: number | null): string {
  if (n == null) return 'N/A'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

export function RankingCard({ item, open, market, days, bt, t, onToggle }: Props) {
  const C = useC()
  const mdd = item.mdd_pct ?? 0
  const vol = item.volatility_annualized_pct ?? 0
  const excess = item.excess_return_vs_index_pct ?? 0
  const mddBar = Math.min(100, Math.abs(mdd)).toFixed(0) + '%'
  const volBar = Math.min(100, Math.abs(vol)).toFixed(0) + '%'

  return (
    <div style={{
      marginBottom: 10, borderRadius: 16, overflow: 'hidden',
      border: `1px solid ${open ? 'rgba(62,123,250,0.35)' : C.cardBorderDefault}`,
      background: C.cardGradient,
      fontFamily: FONT.sans,
    }}>
      {/* Card header button */}
      <button
        onClick={onToggle}
        style={{ width: '100%', border: 'none', background: 'transparent', cursor: 'pointer', textAlign: 'left', padding: '14px 14px 13px', display: 'block', fontFamily: FONT.sans }}
      >
        {/* Top row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
          <span style={{
            fontFamily: FONT.mono, fontSize: 12, fontWeight: 700, color: C.blueSoft,
            background: 'rgba(62,123,250,0.12)', width: 26, height: 26, borderRadius: 8,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            {String(item.rank).padStart(2, '0')}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {item.name ?? item.ticker}
            </div>
            <div style={{ fontFamily: FONT.mono, fontSize: 11, color: C.textDim, marginTop: 2 }}>{item.ticker}</div>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div style={{ fontFamily: FONT.mono, fontSize: 20, fontWeight: 800, color: item.return_pct >= 0 ? C.green : C.red, lineHeight: 1, letterSpacing: '-0.02em' }}>
              {fmtPct(item.return_pct)}
            </div>
            <div style={{ fontSize: 9.5, color: C.textDim, marginTop: 4 }}>{t.moveLabel}</div>
          </div>
        </div>

        {/* Bar row */}
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, marginTop: 13 }}>
          {/* MDD bar */}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 5 }}>
              <span style={{ color: C.textMuted }}>MDD</span>
              <span style={{ fontFamily: FONT.mono, color: C.orange, fontWeight: 600 }}>{fmtPct(mdd)}</span>
            </div>
            <div style={{ height: 5, borderRadius: 3, background: C.barTrack, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: mddBar, background: 'linear-gradient(90deg,#F4A93C,#FF8A4C)', borderRadius: 3 }} />
            </div>
          </div>

          {/* Vol bar */}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 5 }}>
              <span style={{ color: C.textMuted }}>{t.volatilityLabel}</span>
              <span style={{ fontFamily: FONT.mono, color: C.orange, fontWeight: 600 }}>{fmtPct(vol)}</span>
            </div>
            <div style={{ height: 5, borderRadius: 3, background: C.barTrack, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: volBar, background: 'linear-gradient(90deg,#F4A93C,#FF8A4C)', borderRadius: 3 }} />
            </div>
          </div>

          {/* Excess return badge */}
          <span style={{
            fontFamily: FONT.mono, fontSize: 11, color: C.blueSoft,
            background: 'rgba(62,123,250,0.1)', border: '1px solid rgba(62,123,250,0.2)',
            padding: '3px 7px', borderRadius: 7, flexShrink: 0, whiteSpace: 'nowrap',
          }}>
            vs {fmtPct(excess)}
          </span>
        </div>
      </button>

      {/* Backtest panel */}
      {open && (
        <BacktestPanel
          status={bt.status}
          item={bt.item}
          ticker={item.ticker}
          mddPct={item.mdd_pct}
          market={market}
          days={days}
          t={t}
        />
      )}
    </div>
  )
}
