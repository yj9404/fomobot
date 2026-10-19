import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { changeColor } from '../tossColors'
import type { Market, RankingItem } from '../types'
import { getInfoBadgeText, type CommonStrings } from '../i18n/strings'

interface Props {
  item: RankingItem
  market: Market
  t: CommonStrings
}

function fmtPct(n: number): string {
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

/** KOSPI는 원(정수), NASDAQ은 달러(소수 2자리). */
function fmtPrice(price: number, market: Market): string {
  return market === 'kospi'
    ? `${Math.round(price).toLocaleString('ko-KR')}원`
    : `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

/** 토스용 단순 행 — 펼침 없이 순위, 종목명, 기준일 종가, 기간 등락률만 보여준다. */
export function RankingRow({ item, market, t }: Props) {
  const C = useC()
  // 펼침이 없어 ⓘ 팝오버 대신, 해당 종목에만 설명을 행 아래에 그대로 보여준다.
  const note = getInfoBadgeText(item, t)

  return (
    <div style={{ padding: '14px 16px', borderBottom: `1px solid ${C.borderFaint}`, fontFamily: FONT.sans }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{
          fontFamily: FONT.mono, fontSize: 12, fontWeight: 700, color: C.blueSoft,
          background: 'rgba(62,123,250,0.12)',
          width: 28, height: 28, borderRadius: 8, flexShrink: 0,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
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
          <div style={{ fontFamily: FONT.mono, fontSize: 16, fontWeight: 700, color: C.textPrimary }}>
            {item.close_price != null ? fmtPrice(item.close_price, market) : '—'}
          </div>
          <div style={{ fontFamily: FONT.mono, fontSize: 13, fontWeight: 700, marginTop: 3, color: changeColor(item.return_pct, C.textMuted) }}>
            {fmtPct(item.return_pct)}
          </div>
        </div>
      </div>
      {note && <div style={{ marginTop: 8, fontSize: 11.5, lineHeight: 1.5, color: C.textMuted }}>{note}</div>}
    </div>
  )
}
