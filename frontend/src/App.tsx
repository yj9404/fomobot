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
import { StockSearchArea } from './components/StockSearchArea'
import { Footer } from './components/Footer'
import { useRankings } from './hooks/useRankings'
import { useBacktest } from './hooks/useBacktest'
import { useWindowWidth } from './hooks/useWindowWidth'
import { useAdGate } from './hooks/useAdGate'
import { useStrings } from './i18n/strings'
import { useC } from './ThemeContext'
import { PERIODS, RE_PERIODS, RE_DISCLAIMER } from './types'
import { FONT } from './tokens'
import type { Lang, Market, Tab, CapTier } from './types'

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
    if (t === 'stock') {
      url.searchParams.delete('tab')
      url.searchParams.delete('seg')
      url.searchParams.delete('min_price')
      url.searchParams.delete('max_price')
      setReRegion('')
      setReGu('')
      setReDong('')
      setReSeg('')
      setReMinPrice(null)
      setReMaxPrice(null)
    } else {
      url.searchParams.set('tab', t)
    }
    history.replaceState(null, '', url.toString())
  }, [])

  // ── 주식 상태 (기존 그대로) ────────────────────────────────────────────
  const [market, setMarket] = useState<Market>('kospi')
  const [periodIdx, setPeriodIdx] = useState(2) // default: 30d
  const [capTier, setCapTier] = useState<CapTier>('all')
  const [openRank, setOpenRank] = useState<number | null>(null)
  const [selectedRank, setSelectedRank] = useState<number | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  // ── 부동산 상태 ────────────────────────────────────────────────────────
  const [reRegion, setReRegion] = useState('')       // '' = 수도권 전체
  const [rePeriodIdx, setRePeriodIdx] = useState(2)  // 1y
  const [reGu, setReGu] = useState('')               // 5자리 시군구 코드 ('' = 미설정)
  const [reDong, setReDong] = useState('')           // 법정동명 ('' = 미설정)
  const [reSeg, setReSeg] = useState<string>(() => { // 학군 세그먼트 키 ('' = 미선택)
    const p = new URLSearchParams(window.location.search)
    return p.get('seg') ?? ''
  })
  const [reMinPrice, setReMinPrice] = useState<number | null>(() => {
    const v = new URLSearchParams(window.location.search).get('min_price')
    return v !== null && !isNaN(Number(v)) ? Number(v) : null
  })
  const [reMaxPrice, setReMaxPrice] = useState<number | null>(() => {
    const v = new URLSearchParams(window.location.search).get('max_price')
    return v !== null && !isNaN(Number(v)) ? Number(v) : null
  })
  const [reRetryKey, setReRetryKey] = useState(0)
  const [reHasContent, setReHasContent] = useState(false)

  const C = useC()
  const t = useStrings(lang)
  const period = PERIODS[periodIdx]!
  const { status, rankings, disclaimer: stockDisclaimer } = useRankings(market, period.value, capTier, retryKey)
  const { load: loadBt, get: getBt } = useBacktest(market, period.value, period.days)

  useAdGate(tab === 'stock' ? status === 'ok' : reHasContent)

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
    setCapTier('all') // market 변경 시 시총 필터 초기화
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

  const handleReRegion = useCallback((r: string) => {
    setReRegion(r)
    setReGu('')
    setReDong('')
    setReSeg('')
    const url = new URL(window.location.href)
    url.searchParams.delete('seg')
    history.replaceState(null, '', url.toString())
  }, [])

  const handleReGu = useCallback((gu: string, dong: string) => {
    setReGu(gu)
    setReDong(dong)
    if (gu) setReRegion(gu.slice(0, 2))
    else setReRegion('')
    setReSeg('')
    const url = new URL(window.location.href)
    url.searchParams.delete('seg')
    history.replaceState(null, '', url.toString())
  }, [])

  const handleReSeg = useCallback((seg: string) => {
    setReSeg(seg)
    if (seg) {
      setReRegion('')
      setReGu('')
      setReDong('')
    }
    const url = new URL(window.location.href)
    if (seg) url.searchParams.set('seg', seg)
    else url.searchParams.delete('seg')
    history.replaceState(null, '', url.toString())
  }, [])

  const handleReMinPrice = useCallback((v: number | null) => {
    setReMinPrice(v)
    const url = new URL(window.location.href)
    if (v !== null) url.searchParams.set('min_price', String(v))
    else url.searchParams.delete('min_price')
    history.replaceState(null, '', url.toString())
  }, [])

  const handleReMaxPrice = useCallback((v: number | null) => {
    setReMaxPrice(v)
    const url = new URL(window.location.href)
    if (v !== null) url.searchParams.set('max_price', String(v))
    else url.searchParams.delete('max_price')
    history.replaceState(null, '', url.toString())
  }, [])

  const handleReResetFilters = useCallback(() => {
    setReGu('')
    setReDong('')
    setReSeg('')
    setReMinPrice(null)
    setReMaxPrice(null)
    const url = new URL(window.location.href)
    url.searchParams.delete('seg')
    url.searchParams.delete('min_price')
    url.searchParams.delete('max_price')
    history.replaceState(null, '', url.toString())
  }, [])

  // ── 공통 NavRail/FomoHeader props ─────────────────────────────────────
  const sharedControlProps = {
    lang, tab, market, periodIdx, disclaimer, t,
    onLang: setLang,
    onTab: handleTab,
    onMarket: handleMarket,
    onPeriod: handlePeriod,
    capTier, onCapTier: setCapTier,
    reRegion, rePeriodIdx, reGu, reDong, reSeg,
    reMinPrice, reMaxPrice,
    onReRegion: handleReRegion,
    onRePeriod: setRePeriodIdx,
    onReGu: handleReGu,
    onReSeg: handleReSeg,
    onReMinPrice: handleReMinPrice,
    onReMaxPrice: handleReMaxPrice,
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
                <StockSearchArea market={market} lang={lang} t={t} />
                {status === 'loading' && <SkeletonList t={t} />}
                {status === 'empty' && <EmptyState t={t} onRetry={() => { handlePeriod(2); setCapTier('all') }} />}
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
                gu={reGu}
                dong={reDong}
                seg={reSeg}
                minPrice={reMinPrice}
                maxPrice={reMaxPrice}
                retryKey={reRetryKey}
                onRetry={() => setReRetryKey((k) => k + 1)}
                onResetFilters={handleReResetFilters}
                onContentChange={setReHasContent}
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
            <StockSearchArea market={market} lang={lang} t={t} />
            {status === 'loading' && <SkeletonList t={t} />}
            {status === 'empty' && <EmptyState t={t} onRetry={() => { handlePeriod(2); setCapTier('all') }} />}
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
            gu={reGu}
            dong={reDong}
            seg={reSeg}
            minPrice={reMinPrice}
            maxPrice={reMaxPrice}
            retryKey={reRetryKey}
            onRetry={() => setReRetryKey((k) => k + 1)}
            onResetFilters={handleReResetFilters}
            onContentChange={setReHasContent}
            t={t}
          />
        )}

        <Footer lang={lang} style={{ padding: '14px 16px 20px', borderTop: `1px solid ${C.borderSub}` }} />
      </div>
    </div>
  )
}
