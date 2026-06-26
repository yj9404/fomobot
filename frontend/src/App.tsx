import { useState, useCallback } from 'react'
import { FomoHeader } from './components/FomoHeader'
import { NavRail } from './components/NavRail'
import { RankingCard } from './components/RankingCard'
import { RankingTable } from './components/RankingTable'
import { BacktestSidebar } from './components/BacktestSidebar'
import { SkeletonList } from './components/SkeletonList'
import { EmptyState } from './components/EmptyState'
import { ErrorState } from './components/ErrorState'
import { RealEstateView } from './views/RealEstateView'
import { useRankings } from './hooks/useRankings'
import { useBacktest } from './hooks/useBacktest'
import { useWindowWidth } from './hooks/useWindowWidth'
import { useStrings } from './i18n/strings'
import { useC } from './ThemeContext'
import { PERIODS, RE_PERIODS, RE_DISCLAIMER } from './types'
import { FONT } from './tokens'
import type { Lang, Market, Tab, ReLevel } from './types'

function initTab(): Tab {
  const p = new URLSearchParams(window.location.search)
  return p.get('tab') === 'realestate' ? 'realestate' : 'stock'
}

export default function App() {
  const [lang, setLang] = useState<Lang>('ko')

  // ── 최상위 탭 ──────────────────────────────────────────────────────────
  const [tab, setTab] = useState<Tab>(initTab)

  const handleTab = useCallback((t: Tab) => {
    setTab(t)
    const url = new URL(window.location.href)
    if (t === 'stock') url.searchParams.delete('tab')
    else url.searchParams.set('tab', t)
    history.replaceState(null, '', url.toString())
  }, [])

  // ── 주식 상태 (기존 그대로) ────────────────────────────────────────────
  const [market, setMarket] = useState<Market>('kospi')
  const [periodIdx, setPeriodIdx] = useState(2) // default: 30d
  const [openRank, setOpenRank] = useState<number | null>(null)
  const [selectedRank, setSelectedRank] = useState<number | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  // ── 부동산 상태 ────────────────────────────────────────────────────────
  const [reLevel, setReLevel] = useState<ReLevel>('gu')
  const [reRegion, setReRegion] = useState('')       // '' = 수도권 전체
  const [rePeriodIdx, setRePeriodIdx] = useState(2)  // 1y
  const [reRetryKey, setReRetryKey] = useState(0)

  const C = useC()
  const t = useStrings(lang)
  const period = PERIODS[periodIdx]!
  const { status, rankings, disclaimer: stockDisclaimer } = useRankings(market, period.value, retryKey)
  const { load: loadBt, get: getBt } = useBacktest(market, period.value, period.days)

  const windowWidth = useWindowWidth()
  const isDesktop = windowWidth >= 1024

  const disclaimer = tab === 'realestate' ? RE_DISCLAIMER[lang] : stockDisclaimer

  // ── 핸들러 (주식, 기존 그대로) ────────────────────────────────────────
  const handleToggle = useCallback(
    (rank: number, ticker: string) => {
      setOpenRank((prev) => {
        if (prev === rank) return null
        loadBt(ticker)
        return rank
      })
    },
    [loadBt],
  )

  const handleSelect = useCallback(
    (rank: number, ticker: string) => {
      setSelectedRank((prev) => {
        if (prev === rank) return null
        loadBt(ticker)
        return rank
      })
    },
    [loadBt],
  )

  const handleMarket = useCallback((m: Market) => {
    setOpenRank(null)
    setSelectedRank(null)
    setMarket(m)
  }, [])

  const handlePeriod = useCallback((i: number) => {
    setOpenRank(null)
    setSelectedRank(null)
    setPeriodIdx(i)
  }, [])

  const selectedItem = selectedRank != null
    ? (rankings.find((r) => r.rank === selectedRank) ?? null)
    : null
  const emptyBt = { status: 'idle' as const, item: null }

  // ── 공통 NavRail/FomoHeader props ─────────────────────────────────────
  const sharedControlProps = {
    lang, tab, market, periodIdx, disclaimer, t,
    onLang: setLang,
    onTab: handleTab,
    onMarket: handleMarket,
    onPeriod: handlePeriod,
    reLevel, reRegion, rePeriodIdx,
    onReLevel: setReLevel,
    onReRegion: setReRegion,
    onRePeriod: setRePeriodIdx,
  }

  // ── Desktop layout ───────────────────────────────────────────────────
  if (isDesktop) {
    return (
      <div style={{
        minWidth: '100%', minHeight: '100vh', background: C.bg,
        display: 'flex', justifyContent: 'center', fontFamily: FONT.sans,
      }}>
        <div style={{ width: '100%', maxWidth: 1280, display: 'flex', minHeight: '100vh' }}>
          <NavRail {...sharedControlProps} />

          {/* Center column */}
          <div style={{ flex: 1, minWidth: 0, background: C.surface, borderRight: `1px solid ${C.borderSub}` }}>
            {tab === 'stock' && (
              <>
                {status === 'loading' && <SkeletonList t={t} />}
                {status === 'empty' && <EmptyState t={t} onRetry={() => handlePeriod(2)} />}
                {status === 'error' && <ErrorState t={t} onRetry={() => setRetryKey((k) => k + 1)} />}
                {status === 'ok' && (
                  <RankingTable
                    rankings={rankings}
                    selectedRank={selectedRank}
                    market={market}
                    lang={lang}
                    t={t}
                    onSelect={handleSelect}
                  />
                )}
              </>
            )}
            {tab === 'realestate' && (
              <RealEstateView
                lang={lang}
                period={RE_PERIODS[rePeriodIdx]!.value}
                sido={reRegion}
                retryKey={reRetryKey}
                onRetry={() => setReRetryKey((k) => k + 1)}
                t={t}
              />
            )}
          </div>

          {tab === 'stock' && (
            <BacktestSidebar
              selected={selectedItem}
              bt={selectedItem != null ? getBt(selectedItem.ticker) : emptyBt}
              market={market}
              days={period.days}
              lang={lang}
              t={t}
            />
          )}
        </div>
      </div>
    )
  }

  // ── Mobile layout ─────────────────────────────────────────────────────
  return (
    <div style={{
      minWidth: '100%', minHeight: '100vh', background: C.bg,
      display: 'flex', justifyContent: 'center', fontFamily: FONT.sans,
    }}>
      <div style={{ width: '100%', maxWidth: 390, background: C.surface, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <FomoHeader {...sharedControlProps} />

        {tab === 'stock' && (
          <>
            {status === 'loading' && <SkeletonList t={t} />}
            {status === 'empty' && <EmptyState t={t} onRetry={() => handlePeriod(2)} />}
            {status === 'error' && <ErrorState t={t} onRetry={() => setRetryKey((k) => k + 1)} />}
            {status === 'ok' && (
              <div style={{ padding: '12px 14px 16px', borderTop: `1px solid ${C.borderSub}`, flex: 1 }}>
                {rankings.map((item) => (
                  <RankingCard
                    key={item.ticker}
                    item={item}
                    open={openRank === item.rank}
                    market={market}
                    days={period.days}
                    bt={getBt(item.ticker)}
                    t={t}
                    onToggle={() => handleToggle(item.rank, item.ticker)}
                  />
                ))}
                <div style={{ textAlign: 'center', fontSize: 11, color: C.textDim, fontFamily: FONT.mono, paddingTop: 2 }}>
                  {lang === 'ko'
                    ? `Top ${rankings.length} · 카드를 눌러 백테스트 확인`
                    : `Top ${rankings.length} · tap a card to see backtest`}
                </div>
              </div>
            )}
          </>
        )}

        {tab === 'realestate' && (
          <RealEstateView
            lang={lang}
            period={RE_PERIODS[rePeriodIdx]!.value}
            sido={reRegion}
            retryKey={reRetryKey}
            onRetry={() => setReRetryKey((k) => k + 1)}
            t={t}
          />
        )}
      </div>
    </div>
  )
}
