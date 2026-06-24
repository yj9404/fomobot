import { C, FONT } from '../tokens'
import type { RankingItem, Market, Lang } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  rankings: RankingItem[]
  selectedRank: number | null
  market: Market
  lang: Lang
  t: Strings
  onSelect: (rank: number, ticker: string) => void
}

function fmtPct(n: number | null): string {
  if (n == null) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

export function RankingTable({ rankings, selectedRank, lang, t, onSelect }: Props) {
  const vsLabel = lang === 'ko' ? 'vs 지수' : 'vs Index'

  return (
    <div style={{ fontFamily: FONT.sans, padding: '20px 20px 24px' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${C.border}` }}>
            <th style={{ ...th, textAlign: 'center', width: 44 }}>#</th>
            <th style={{ ...th, textAlign: 'left', paddingLeft: 12 }}>
              {lang === 'ko' ? '종목' : 'Stock'}
            </th>
            <th style={th}>{t.moveLabel}</th>
            <th style={th}>MDD</th>
            <th style={th}>{t.volatilityLabel}</th>
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
                onClick={() => onSelect(item.rank, item.ticker)}
                style={{
                  cursor: 'pointer',
                  borderBottom: `1px solid ${C.borderFaint}`,
                  background: selected ? 'rgba(62,123,250,0.07)' : 'transparent',
                  outline: selected ? `1px solid rgba(62,123,250,0.2)` : 'none',
                  outlineOffset: -1,
                }}
                onMouseEnter={(e) => {
                  if (!selected) (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(255,255,255,0.025)'
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLTableRowElement).style.background = selected ? 'rgba(62,123,250,0.07)' : 'transparent'
                }}
              >
                {/* Rank */}
                <td style={{ ...td, textAlign: 'center' }}>
                  <span style={{
                    fontFamily: FONT.mono, fontSize: 12, fontWeight: 700, color: C.blueSoft,
                    background: 'rgba(62,123,250,0.12)', width: 28, height: 28, borderRadius: 8,
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {String(item.rank).padStart(2, '0')}
                  </span>
                </td>

                {/* Name / ticker */}
                <td style={{ ...td, paddingLeft: 12 }}>
                  <div style={{ fontSize: 14.5, fontWeight: 700, color: C.textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 200 }}>
                    {item.name ?? item.ticker}
                  </div>
                  <div style={{ fontFamily: FONT.mono, fontSize: 11, color: C.textDim, marginTop: 2 }}>{item.ticker}</div>
                </td>

                {/* Return */}
                <td style={{ ...td, textAlign: 'right' }}>
                  <span style={{ fontFamily: FONT.mono, fontSize: 16, fontWeight: 800, color: positive ? C.green : C.red }}>
                    {fmtPct(item.return_pct)}
                  </span>
                </td>

                {/* MDD */}
                <td style={{ ...td, textAlign: 'right' }}>
                  <span style={{ fontFamily: FONT.mono, fontSize: 13, fontWeight: 600, color: C.orange }}>
                    {fmtPct(item.mdd_pct)}
                  </span>
                </td>

                {/* Volatility */}
                <td style={{ ...td, textAlign: 'right' }}>
                  <span style={{ fontFamily: FONT.mono, fontSize: 13, fontWeight: 600, color: C.orange }}>
                    {fmtPct(item.volatility_annualized_pct)}
                  </span>
                </td>

                {/* Excess return badge */}
                <td style={{ ...td, textAlign: 'center' }}>
                  <span style={{
                    fontFamily: FONT.mono, fontSize: 11, color: C.blueSoft,
                    background: 'rgba(62,123,250,0.1)', border: '1px solid rgba(62,123,250,0.2)',
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
}

const td: React.CSSProperties = {
  padding: '14px 8px',
  verticalAlign: 'middle',
}
