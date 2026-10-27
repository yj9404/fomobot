import { useLayoutEffect, useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { changeColor } from '../tossColors'
import { displayStockName, fmtPrice } from '../format'
import { TossBanner } from '../components/TossBanner'
import { ErrorState } from '../components/ErrorState'
import { TOSS_STR, TOSS_UI } from '../i18n/strings.toss'
import { PERIODS } from '../types'
import type { Market, Period } from '../types'
import { useStockDetail, type StockDetail } from './api'
import { fmtPct, listedWithin, sliceSeries } from './detail'
import { PriceChart } from './PriceChart'
import { ShareAction } from './ShareAction'
import { useRouter } from './router'
import { DEFAULT_RANKINGS } from './routes'

// 차트 구간 탭. 1일은 선이 성립하지 않아 뺀다.
const CHART_PERIODS = PERIODS.filter((p) => p.value !== '1d')
const DEFAULT_CHART: Period = '365d'

/**
 * 종목 상세. 종가, 차트, 기간별 등락률만 보여준다 — 매수 시점·투자금 계산 같은 표현은 두지 않는다.
 * 배너는 콘텐츠가 실제로 화면을 넘칠 때만 맨 아래에 붙인다(스크롤되는 화면에만, 한 개).
 */
export function StockScreen({ market, ticker }: { market: Market; ticker: string }) {
  const C = useC()
  const { depth, push } = useRouter()
  const [retryKey, setRetryKey] = useState(0)
  const state = useStockDetail(market, ticker, retryKey)

  // 공유 링크로 상세에 바로 들어온 경우(앱 안 첫 화면) 순위로 갈 길을 둔다. 뒤로가기는 종료다.
  const toRankings = depth === 0 && (
    <div style={{ padding: '8px 16px 24px' }}>
      <button
        onClick={() => push({ ...DEFAULT_RANKINGS, market })}
        style={{
          width: '100%', padding: '14px 0', borderRadius: 12, border: `1px solid ${C.borderSub}`,
          background: C.surface, color: C.textSub, fontSize: 15, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer',
        }}
      >
        {TOSS_UI.allRankings}
      </button>
    </div>
  )

  return (
    <div style={{ fontFamily: FONT.sans, flex: 1, display: 'flex', flexDirection: 'column' }}>
      {state.status === 'loading' && (
        <div style={{ padding: '64px 0', textAlign: 'center', fontSize: 13, color: C.textDim }}>{TOSS_STR.loadingSub}</div>
      )}
      {state.status === 'error' && <ErrorState t={TOSS_STR} onRetry={() => setRetryKey((k) => k + 1)} />}
      {state.status === 'not_found' && <Notice title={TOSS_UI.notFoundTitle} sub={TOSS_UI.notFoundSub} />}
      {state.status === 'ok' && <Detail d={state.data} footer={toRankings} />}
      {(state.status === 'error' || state.status === 'not_found') && toRankings}
    </div>
  )
}

function Notice({ title, sub, name }: { title: string; sub: string; name?: string }) {
  const C = useC()
  return (
    <div style={{ padding: '56px 24px', textAlign: 'center' }}>
      {name && <div style={{ fontSize: 13, color: C.textMuted, marginBottom: 10 }}>{name}</div>}
      <div style={{ fontSize: 16, fontWeight: 700, color: C.textPrimary }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: 13, color: C.textMuted, lineHeight: 1.5 }}>{sub}</div>
    </div>
  )
}

function Detail({ d, footer }: { d: StockDetail; footer: React.ReactNode }) {
  const C = useC()
  const [chartPeriod, setChartPeriod] = useState<Period>(DEFAULT_CHART)
  const [showBanner, setShowBanner] = useState(false)

  // 배너 없이 그린 콘텐츠가 이미 화면보다 길 때만 배너를 붙인다. 데이터가 그려진 직후 한 번만 잰다.
  useLayoutEffect(() => {
    setShowBanner(document.documentElement.scrollHeight > window.innerHeight)
  }, [])

  const name = displayStockName(d.name)
  if (d.status === 'correcting') return <><Notice name={name} title={TOSS_UI.correctingTitle} sub={TOSS_UI.correctingSub} />{footer}</>
  if (d.status === 'no_data' || d.close == null || !d.as_of) return <><Notice name={name} title={TOSS_UI.noDataTitle} sub={TOSS_UI.noDataSub} />{footer}</>

  const asOf = d.as_of
  const day = d.changes['1d']
  const stale = d.close_date != null && d.close_date < asOf
  const chartDays = PERIODS.find((p) => p.value === chartPeriod)!.days
  const badge: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: C.textMuted, background: C.surfaceAlt, padding: '3px 8px', borderRadius: 6,
  }
  const chip = (active: boolean): React.CSSProperties => ({
    flex: 1, padding: '9px 0', minHeight: 40, borderRadius: 10, border: 'none', cursor: 'pointer',
    fontSize: 13, fontWeight: 600, fontFamily: FONT.sans,
    background: active ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
    color: active ? C.blueSoft : C.textMuted,
  })

  return (
    <>
      {/* 종목·종가 */}
      <div style={{ padding: '20px 16px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: FONT.mono, fontSize: 12, color: C.textDim }}>{d.ticker}</span>
          <span style={{ ...badge, color: C.blueSoft, background: 'rgba(62,123,250,0.12)' }}>{d.market.toUpperCase()}</span>
          {stale && <span style={badge}>{TOSS_UI.lastTraded(d.close_date!)}</span>}
          {!d.is_active && <span style={badge}>{TOSS_UI.delisted}</span>}
        </div>
        <div style={{ marginTop: 6, fontSize: 22, fontWeight: 800, color: C.textPrimary, lineHeight: 1.3, wordBreak: 'keep-all' }}>{name}</div>
        <div style={{ marginTop: 12, fontFamily: FONT.mono, fontSize: 30, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.02em' }}>
          {fmtPrice(d.close, d.market)}
        </div>
        {day && (
          <div style={{ marginTop: 4, fontSize: 14, color: C.textMuted }}>
            {TOSS_UI.prevDay}{' '}
            <span style={{ fontFamily: FONT.mono, fontWeight: 700, color: changeColor(day.change_pct, C.textMuted) }}>{fmtPct(day.change_pct)}</span>
          </div>
        )}
        <div style={{ marginTop: 6, fontSize: 11.5, color: C.textDim }}>
          {TOSS_STR.asOfLabel} {asOf} {TOSS_STR.closeNote}
        </div>
      </div>

      {/* 차트 */}
      <PriceChart points={sliceSeries(d.series, asOf, chartDays)} market={d.market} />
      <div style={{ display: 'flex', gap: 6, padding: '12px 16px 4px' }}>
        {CHART_PERIODS.map((p) => (
          <button key={p.value} onClick={() => setChartPeriod(p.value as Period)} style={chip(chartPeriod === p.value)}>
            {p.label.ko}
          </button>
        ))}
      </div>

      <div style={{ padding: '12px 16px 0' }}>
        <ShareAction route={{ name: 'stock', market: d.market, ticker: d.ticker }} asOf={asOf} message={TOSS_UI.stockShareMessage(name)} />
      </div>

      {/* 기간별 등락률 */}
      <div style={{ padding: '20px 16px 4px', fontSize: 14, fontWeight: 700, color: C.textPrimary }}>{TOSS_UI.periodChanges}</div>
      {PERIODS.map((p) => {
        const ch = d.changes[p.value as Period]
        const since = listedWithin(d, p.value as Period)
        return (
          <div key={p.value} style={{ display: 'flex', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${C.borderFaint}` }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, color: C.textSub }}>{p.label.ko}</div>
              {since && <div style={{ marginTop: 2, fontSize: 11.5, color: C.textDim }}>{TOSS_UI.sinceListing(since)}</div>}
            </div>
            <div style={{ fontFamily: FONT.mono, fontSize: 15, fontWeight: 700, color: ch ? changeColor(ch.change_pct, C.textMuted) : C.textDim }}>
              {ch ? fmtPct(ch.change_pct) : '—'}
            </div>
          </div>
        )
      })}

      <div style={{ padding: '14px 16px 16px', fontSize: 11.5, color: C.textDim, lineHeight: 1.5 }}>{TOSS_STR.disclaimer}</div>

      {footer}
      {showBanner && <TossBanner />}
    </>
  )
}
