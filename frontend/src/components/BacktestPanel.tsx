import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { Sparkline, buildSparkSeries } from './Sparkline'
import type { BacktestItem, Market } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  status: 'idle' | 'loading' | 'ok' | 'error'
  item: BacktestItem | null
  ticker: string
  mddPct: number | null
  market: Market
  days: number
  t: Strings
}

function fmtPct(n: number | null): string {
  if (n == null) return 'N/A'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

function fmtMoney(v: number, market: Market): string {
  if (market === 'kospi') return '₩' + Math.round(v).toLocaleString('ko-KR')
  return '$' + Math.round(v).toLocaleString('en-US')
}

export function BacktestPanel({ status, item, ticker, mddPct, market, days, t }: Props) {
  const C = useC()

  const panelStyle: React.CSSProperties = {
    background: C.surfaceBt,
    borderTop: '1px solid rgba(62,123,250,0.22)',
    borderLeft: `3px solid ${C.blue}`,
    padding: '15px 16px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    fontFamily: FONT.sans,
  }

  if (status === 'loading' || status === 'idle') {
    return (
      <div style={panelStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid rgba(62,123,250,0.25)', borderTopColor: C.blue, animation: 'fb-spin .8s linear infinite' }} />
          <span style={{ fontSize: 12, color: C.textDim }}>{t.btLoading}</span>
        </div>
      </div>
    )
  }

  if (status === 'error' || item == null) {
    return (
      <div style={panelStyle}>
        <span style={{ fontSize: 12, color: C.textDim }}>{t.noBacktest}</span>
      </div>
    )
  }

  const ret = item.current_return_pct
  const profit = ret == null || ret >= 0
  const color = profit ? C.green : C.red
  const fill = profit ? C.greenFill : C.redFill
  const invested = market === 'kospi' ? 1_000_000 : 10_000
  const nowVal = ret != null ? invested * (1 + ret / 100) : invested
  const dip = mddPct != null ? -(Math.round(Math.abs(mddPct) * 0.62 * 10) / 10) : null
  const sparkData = buildSparkSeries(ticker + 'b', ret ?? 0, 22)
  const buyLabel = t.buyPre + days + t.buySuf
  const quip = profit ? t.profitQuip : t.lossQuip

  return (
    <div style={panelStyle}>
      {/* Title + buy label */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: C.textPrimary }}>{t.btTitle}</span>
        <span style={{ fontSize: 10.5, fontWeight: 600, color: C.blueSoft, background: 'rgba(62,123,250,0.12)', padding: '3px 9px', borderRadius: 7, fontFamily: FONT.mono }}>{buyLabel}</span>
      </div>

      {/* Return + sparkline */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14 }}>
        <div style={{ flexShrink: 0 }}>
          <div style={{ fontSize: 11, color: C.textMuted }}>{t.btReturn}</div>
          <div style={{ fontFamily: FONT.mono, fontSize: 34, fontWeight: 800, color, lineHeight: 1.05, letterSpacing: '-0.02em' }}>{fmtPct(ret)}</div>
        </div>
        <Sparkline data={sparkData} width={120} height={40} color={color} fill={fill} />
      </div>

      {/* Invested → now */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, fontFamily: FONT.mono }}>
        <span style={{ color: C.textMuted }}>{fmtMoney(invested, market)}</span>
        <span style={{ color: C.textDim }}>→</span>
        <span style={{ color, fontWeight: 600 }}>{fmtMoney(nowVal, market)}</span>
      </div>

      {/* MDD dip warning */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 11, color: '#C99A52', background: C.orangeFill, padding: '7px 9px', borderRadius: 8 }}>
        <span style={{ color: C.orange }}>⚠</span>
        <span>{t.btPath}</span>
        <span style={{ fontFamily: FONT.mono, fontWeight: 600 }}>{fmtPct(dip)}</span>
      </div>

      {/* Quip */}
      <div style={{ fontSize: 12.5, color: C.textMuted, fontStyle: 'italic' }}>"{quip}"</div>
    </div>
  )
}
