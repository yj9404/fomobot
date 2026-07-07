import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { Sparkline } from './Sparkline'
import type { BacktestDetailResponse, Market, Lang } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  status: 'idle' | 'loading' | 'ok' | 'error'
  detail: BacktestDetailResponse | null
  market: Market
  days: number
  lang: Lang
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

const EN_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "YYYY-MM-DD" → "2022년 2월부터" / "Since Feb 2022" */
function fmtSince(dateStr: string, lang: Lang): string {
  const [y, m] = dateStr.split('-').map(Number)
  if (lang === 'ko') return `${y}년 ${m}월부터`
  return `Since ${EN_MONTHS[(m ?? 1) - 1]} ${y}`
}

export function BacktestPanel({ status, detail, market, days, lang, t }: Props) {
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

  // DCA가 메인. 1d/7d 등 DCA가 성립하지 않는 기간(scenarios.dca === null)은
  // buy-and-hold로 폴백한다.
  const dca = detail?.scenarios.dca ?? null
  const bh = detail?.scenarios.buy_and_hold ?? null
  const main = dca ?? bh

  if (status === 'error' || detail == null || main == null) {
    return (
      <div style={panelStyle}>
        <span style={{ fontSize: 12, color: C.textDim }}>{t.noBacktest}</span>
      </div>
    )
  }

  const isDcaMain = dca != null
  const ret = main.final_return_pct
  const profit = ret >= 0
  const color = profit ? C.green : C.red
  const fill = profit ? C.greenFill : C.redFill

  // 백엔드가 이미 원(₩) 단위로 정규화해 준 equity_curve를 그대로 쓴다 — 재계산 없음.
  const equityValues = main.equity_curve.map((p) => p.value)
  const finalValue = equityValues.length > 0 ? equityValues[equityValues.length - 1]! : detail.principal

  const badgeLabel = isDcaMain ? t.btDcaBadge : t.buyPre + days + t.buySuf

  // buy-and-hold 한 줄 대비 — DCA가 메인일 때만 보여준다(그게 아니면 이미 메인이라 중복).
  const compareRet = isDcaMain ? bh?.final_return_pct ?? null : null

  // 결손 경고: executed_installments < total_installments 일 때만. first_traded_date는
  // 결손이 없는 종목에서는 "상장일"이 아니므로(실측 확인됨) 이 조건 밖에서는 쓰지 않는다.
  const showDeficitWarning =
    dca != null &&
    dca.executed_installments != null &&
    dca.total_installments != null &&
    dca.executed_installments < dca.total_installments &&
    detail.first_traded_date != null

  const quip = profit ? t.profitQuip : t.lossQuip

  return (
    <div style={panelStyle}>
      {/* Title + badge */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: C.textPrimary }}>{t.btTitle}</span>
        <span style={{ fontSize: 10.5, fontWeight: 600, color: C.blueSoft, background: 'rgba(62,123,250,0.12)', padding: '3px 9px', borderRadius: 7, fontFamily: FONT.mono }}>{badgeLabel}</span>
      </div>

      {/* Return + sparkline (메인 시나리오의 실제 equity curve) */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14 }}>
        <div style={{ flexShrink: 0 }}>
          <div style={{ fontSize: 11, color: C.textMuted }}>{t.btReturn}</div>
          <div style={{ fontFamily: FONT.mono, fontSize: 34, fontWeight: 800, color, lineHeight: 1.05, letterSpacing: '-0.02em' }}>{fmtPct(ret)}</div>
        </div>
        <Sparkline data={equityValues} width={120} height={40} color={color} fill={fill} />
      </div>

      {/* 원금 → 최종 평가액 (백엔드가 준 원 단위 값 그대로) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 12, fontFamily: FONT.mono }}>
        <span style={{ color: C.textMuted }}>{fmtMoney(detail.principal, market)}</span>
        <span style={{ color: C.textDim }}>→</span>
        <span style={{ color, fontWeight: 600 }}>{fmtMoney(finalValue, market)}</span>
      </div>

      {/* MDD dip — 메인 시나리오의 실측 MDD */}
      {main.mdd_pct != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 11, color: '#C99A52', background: C.orangeFill, padding: '7px 9px', borderRadius: 8 }}>
          <span style={{ color: C.orange }}>⚠</span>
          <span>{t.btPath}</span>
          <span style={{ fontFamily: FONT.mono, fontWeight: 600 }}>{fmtPct(main.mdd_pct)}</span>
        </div>
      )}

      {/* 결손 경고 — 상장 지연 등으로 일부 회차만 집행됐을 때만 */}
      {showDeficitWarning && (
        <div
          title={fmtSince(detail.first_traded_date!, lang)}
          style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 11, color: '#C99A52', background: C.orangeFill, padding: '7px 9px', borderRadius: 8, cursor: 'help' }}
        >
          <span style={{ color: C.orange }}>ℹ</span>
          <span>{t.btDeficitWarning}</span>
        </div>
      )}

      {/* buy-and-hold 한 줄 대비 — DCA가 메인일 때만 */}
      {compareRet != null && (
        <div style={{ fontSize: 12, color: C.textMuted, fontFamily: FONT.mono }}>
          {t.btCompareLumpSum} {fmtPct(compareRet)}
        </div>
      )}

      {/* Quip */}
      <div style={{ fontSize: 12.5, color: C.textMuted, fontStyle: 'italic' }}>"{quip}"</div>
    </div>
  )
}
