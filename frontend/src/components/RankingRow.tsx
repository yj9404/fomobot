import { useC, useTheme } from '../ThemeContext'
import { FONT, DECLINE_ACCENT_LIGHT } from '../tokens'
import type { RankingItem } from '../types'
import { getInfoBadgeText, type CommonStrings } from '../i18n/strings'

interface Props {
  item: RankingItem
  t: CommonStrings
}

function fmtPct(n: number): string {
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

/** 토스용 단순 행 — 펼침 없이 순위, 종목명, 기간 등락률만 보여준다. */
export function RankingRow({ item, t }: Props) {
  const C = useC()
  const { atmosphereMode } = useTheme()
  const isFall = atmosphereMode === 'fall'
  const da = DECLINE_ACCENT_LIGHT
  // 펼침이 없어 ⓘ 팝오버 대신, 해당 종목에만 설명을 행 아래에 그대로 보여준다.
  const note = getInfoBadgeText(item, t)

  return (
    <div style={{ padding: '14px 16px', borderBottom: `1px solid ${C.borderFaint}`, fontFamily: FONT.sans }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{
          fontFamily: FONT.mono, fontSize: 12, fontWeight: 700,
          color: isFall ? da.badgeText : C.blueSoft,
          background: isFall ? da.badgeBg : 'rgba(62,123,250,0.12)',
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
          <div style={{ fontFamily: FONT.mono, fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em', color: item.return_pct >= 0 ? C.green : C.red }}>
            {fmtPct(item.return_pct)}
          </div>
          <div style={{ fontSize: 9.5, color: C.textDim, marginTop: 3 }}>{t.moveLabel}</div>
        </div>
      </div>
      {note && <div style={{ marginTop: 8, fontSize: 11.5, lineHeight: 1.5, color: C.textMuted }}>{note}</div>}
    </div>
  )
}
