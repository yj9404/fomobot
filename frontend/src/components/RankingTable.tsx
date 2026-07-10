import { useC, useTheme } from '../ThemeContext'
import { FONT, DECLINE_ACCENT_DARK, DECLINE_ACCENT_LIGHT } from '../tokens'
import { NewsDot } from './NewsDot'
import type { RankingItem, Market, Lang, Period } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  rankings: RankingItem[]
  selectedRank: number | null
  market: Market
  lang: Lang
  t: Strings
  period: Period
  asOf: string
  onSelect: (rank: number, ticker: string, hasNews: boolean | null | undefined) => void
}

function fmtPct(n: number | null): string {
  if (n == null) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

export function RankingTable({ rankings, selectedRank, lang, t, period, asOf, onSelect }: Props) {
  const C = useC()
  const { theme, atmosphereMode } = useTheme()
  const da = theme === 'dark' ? DECLINE_ACCENT_DARK : DECLINE_ACCENT_LIGHT
  const isFall = atmosphereMode === 'fall'
  const vsLabel = lang === 'ko' ? 'vs 지수' : 'vs Index'
  // "전일(1d)"은 가격 포인트가 2개뿐이라 MDD·변동성이 통계적으로 의미가 없음
  // (MDD는 상승 종목이면 항상 0, 변동성은 표본 1개라 정의 자체가 안 됨) — 컬럼 자체를 숨긴다.
  const showRiskMetrics = period !== '1d'

  const th: React.CSSProperties = {
    padding: '10px 8px 13px',
    fontSize: 11,
    fontWeight: 600,
    color: C.textDim,
    fontFamily: FONT.sans,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    textAlign: 'right',
    whiteSpace: 'nowrap',
    borderBottom: `1px solid ${C.border}`,
  }

  const td: React.CSSProperties = {
    padding: '15px 8px',
    verticalAlign: 'middle',
  }

  return (
    <div style={{ fontFamily: FONT.sans, padding: '20px 20px 24px' }}>
      {asOf && (
        <div style={{
          fontSize: 11, color: C.textDim, fontFamily: FONT.mono,
          marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span>{t.asOfLabel}</span>
          <span style={{ color: C.textSub, fontWeight: 600 }}>{asOf}</span>
        </div>
      )}
      <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 5px' }}>
        <thead>
          <tr>
            <th style={{ ...th, textAlign: 'center', width: 44 }}>#</th>
            <th style={{ ...th, textAlign: 'left', paddingLeft: 12 }}>
              {lang === 'ko' ? '종목' : 'Stock'}
            </th>
            <th style={th}>{t.moveLabel}</th>
            {showRiskMetrics && <th style={th}>MDD</th>}
            {showRiskMetrics && <th style={th}>{t.volatilityLabel}</th>}
            <th style={{ ...th, textAlign: 'center' }}>{vsLabel}</th>
          </tr>
        </thead>
        <tbody>
          {rankings.map((item) => {
            const selected = selectedRank === item.rank
            const positive = item.return_pct >= 0
            return (
              <tr
                key={item.ticker}
                onClick={() => onSelect(item.rank, item.ticker, item.has_news)}
                style={{
                  cursor: 'pointer',
                  borderRadius: 10,
                  background: selected ? 'rgba(62,123,250,0.07)' : C.cardGradient,
                  boxShadow: `0 0 0 1px ${selected ? 'rgba(62,123,250,0.35)' : C.cardBorderDefault}`,
                }}
                onMouseEnter={(e) => {
                  if (!selected) (e.currentTarget as HTMLTableRowElement).style.background = C.hoverBg
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLTableRowElement).style.background = selected ? 'rgba(62,123,250,0.07)' : C.cardGradient
                }}
              >
                {/* Rank */}
                <td style={{ ...td, textAlign: 'center' }}>
                  <span style={{
                    fontFamily: FONT.mono, fontSize: 12, fontWeight: 700,
                    color: isFall ? da.badgeText : C.blueSoft,
                    background: isFall ? da.badgeBg : 'rgba(62,123,250,0.12)',
                    width: 28, height: 28, borderRadius: 8,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {String(item.rank).padStart(2, '0')}
                  </span>
                </td>

                {/* Name / ticker */}
                <td style={{ ...td, paddingLeft: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <NewsDot show={item.has_news === true} t={t} />
                    <span style={{ fontSize: 14.5, fontWeight: 700, color: C.textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 200 }}>
                      {item.name ?? item.ticker}
                    </span>
                  </div>
                  <div style={{ fontFamily: FONT.mono, fontSize: 11, color: C.textDim, marginTop: 2 }}>{item.ticker}</div>
                </td>

                {/* Return */}
                <td style={{ ...td, textAlign: 'right' }}>
                  <span style={{ fontFamily: FONT.mono, fontSize: 16, fontWeight: 800, color: positive ? C.green : C.red }}>
                    {fmtPct(item.return_pct)}
                  </span>
                </td>

                {/* MDD — 전일(1d)은 2포인트뿐이라 의미 없어 컬럼 자체를 숨김 */}
                {showRiskMetrics && (
                  <td style={{ ...td, textAlign: 'right' }}>
                    <span style={{ fontFamily: FONT.mono, fontSize: 13, fontWeight: 600, color: C.orange }}>
                      {fmtPct(item.mdd_pct)}
                    </span>
                  </td>
                )}

                {/* Volatility — 전일(1d)은 표본 1개라 정의 자체가 안 됨 */}
                {showRiskMetrics && (
                  <td style={{ ...td, textAlign: 'right' }}>
                    <span style={{ fontFamily: FONT.mono, fontSize: 13, fontWeight: 600, color: C.orange }}>
                      {fmtPct(item.volatility_annualized_pct)}
                    </span>
                  </td>
                )}

                {/* Excess return badge */}
                <td style={{ ...td, textAlign: 'center' }}>
                  <span style={{
                    fontFamily: FONT.mono, fontSize: 11,
                    color: isFall ? da.badgeText : C.blueSoft,
                    background: isFall ? da.badgeBg : 'rgba(62,123,250,0.1)',
                    border: isFall ? `1px solid ${da.badgeBorder}` : '1px solid rgba(62,123,250,0.2)',
                    padding: '3px 8px', borderRadius: 7, whiteSpace: 'nowrap',
                  }}>
                    {fmtPct(item.excess_return_vs_index_pct)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div style={{ textAlign: 'center', fontSize: 11, color: C.textDim, fontFamily: FONT.mono, paddingTop: 18 }}>
        Top {rankings.length} &nbsp;·&nbsp;
        {lang === 'ko' ? '행을 클릭하면 백테스트를 확인할 수 있어요' : 'click a row to see backtest'}
      </div>
    </div>
  )
}
