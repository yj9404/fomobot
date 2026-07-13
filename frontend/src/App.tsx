import { useState, useCallback, useEffect } from 'react'
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
import { BreadthWidget } from './components/BreadthWidget'
import { Footer } from './components/Footer'
import { AdFitUnit } from './components/AdFitUnit'
import { useRankings } from './hooks/useRankings'
import { useBacktestDetail } from './hooks/useBacktestDetail'
import { useNewsCache } from './hooks/useNewsCache'
import { useWindowWidth } from './hooks/useWindowWidth'
import { useAdGate } from './hooks/useAdGate'
import { useStrings } from './i18n/strings'
import { useC, useTheme } from './ThemeContext'
import { PERIODS, RE_PERIODS, RE_DISCLAIMER } from './types'
import { FONT } from './tokens'
import { fetchStockNews } from './api/stock'
import type { Lang, Market, OrderDir, Tab, CapTier } from './types'

function initTab(): Tab {
  const p = new URLSearchParams(window.location.search)
  return p.get('tab') === 'realestate' ? 'realestate' : 'stock'
}

function initOrder(forTab: Tab): OrderDir {
  const current = initTab()
  if (current !== forTab) return 'desc'
  const v = new URLSearchParams(window.location.search).get('order')
  return v === 'asc' ? 'asc' : 'desc'
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
      url.searchParams.delete('order')
      setReRegion('')
      setReGu('')
      setReDong('')
      setReSeg('')
      setReMinPrice(null)
      setReMaxPrice(null)
    } else {
      url.searchParams.set('tab', t)
      url.searchParams.delete('order')
    }
    history.replaceState(null, '', url.toString())
  }, [])

  // ── 주식 상태 ────────────────────────────────────────────────────────
  const [market, setMarket] = useState<Market>('kospi')
  const [periodIdx, setPeriodIdx] = useState(2) // default: 30d
  const [capTier, setCapTier] = useState<CapTier>('all')
  const [stockOrder, setStockOrder] = useState<OrderDir>(() => initOrder('stock'))
  const [openRank, setOpenRank] = useState<number | null>(null)
  const [selectedRank, setSelectedRank] = useState<number | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  // ── 부동산 상태 ────────────────────────────────────────────────────────
  const [reRegion, setReRegion] = useState('')
  const [rePeriodIdx, setRePeriodIdx] = useState(2)  // 1y
  const [reGu, setReGu] = useState('')
  const [reDong, setReDong] = useState('')
  const [reSeg, setReSeg] = useState<string>(() => {
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
  const [reOrder, setReOrder] = useState<OrderDir>(() => initOrder('realestate'))
  const [reRetryKey, setReRetryKey] = useState(0)
  const [reHasContent, setReHasContent] = useState(false)

  const { setAtmosphereMode } = useTheme()
  const C = useC()
  const t = useStrings(lang)
  const period = PERIODS[periodIdx]!
  const { status, rankings, disclaimer: stockDisclaimer, asOf } = useRankings(market, period.value, capTier, retryKey, stockOrder)
  const { load: loadBtDetail, get: getBtDetail } = useBacktestDetail(market, period.value, asOf)
  const { load: loadNews, get: getNews } = useNewsCache(fetchStockNews)

  const hasContent = tab === 'stock' ? status === 'ok' : reHasContent
  useAdGate(hasContent)

  const windowWidth = useWindowWidth()
  const isDesktop = windowWidth >= 1024

  const disclaimer = tab === 'realestate' ? RE_DISCLAIMER[lang] : stockDisclaimer

  // ── 분위기 모드 동기화 ─────────────────────────────────────────────────
  useEffect(() => {
    const order = tab === 'stock' ? stockOrder : reOrder
    setAtmosphereMode(order === 'asc' ? 'fall' : 'rise')
  }, [tab, stockOrder, reOrder, setAtmosphereMode])

  // ── 주식 핸들러 ────────────────────────────────────────────────────────
  const handleToggle = useCallback(
    (rank: number, ticker: string, hasNews: boolean | null | undefined) => {
      setOpenRank((prev) => {
        if (prev === rank) return null
        loadBtDetail(ticker)
        if (hasNews === true) loadNews(ticker)
        return rank
      })
    },
    [loadBtDetail, loadNews],
  )

  const handleSelect = useCallback(
    (rank: number, ticker: string, hasNews: boolean | null | undefined) => {
      setSelectedRank((prev) => {
        if (prev === rank) return null
        loadBtDetail(ticker)
        if (hasNews === true) loadNews(ticker)
        return rank
      })
    },
    [loadBtDetail, loadNews],
  )

  const handleMarket = useCallback((m: Market) => {
    setOpenRank(null)
    setSelectedRank(null)
    setCapTier('all')
    setMarket(m)
  }, [])

  const handlePeriod = useCallback((i: number) => {
    setOpenRank(null)
    setSelectedRank(null)
    setPeriodIdx(i)
  }, [])

  const handleStockOrder = useCallback((o: OrderDir) => {
    setStockOrder(o)
    setOpenRank(null)
    setSelectedRank(null)
    const url = new URL(window.location.href)
    if (o === 'asc') url.searchParams.set('order', 'asc')
    else url.searchParams.delete('order')
    history.replaceState(null, '', url.toString())
  }, [])

  const selectedItem = selectedRank != null
    ? (rankings.find((r) => r.rank === selectedRank) ?? null)
    : null
  const emptyBtDetail = { status: 'idle' as const, detail: null }
  const emptyNewsDetail = { status: 'idle' as const, articles: [] }

  // ── 부동산 핸들러 ──────────────────────────────────────────────────────
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

  const handleReOrder = useCallback((o: OrderDir) => {
    setReOrder(o)
    const url = new URL(window.location.href)
    if (o === 'asc') url.searchParams.set('order', 'asc')
    else url.searchParams.delete('order')
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
    stockOrder, onStockOrder: handleStockOrder,
    reRegion, rePeriodIdx, reGu, reDong, reSeg,
    reMinPrice, reMaxPrice,
    reOrder, onReOrder: handleReOrder,
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
        transition: 'background-color 0.25s ease',
      }}>
        <div style={{ width: '100%', maxWidth: 1280, display: 'flex', minHeight: '100vh' }}>
          <NavRail {...sharedControlProps} />

          {/* Center column */}
          <div style={{
            flex: 1, minWidth: 0, background: C.surface, borderRight: `1px solid ${C.borderSub}`,
            transition: 'background-color 0.25s ease',
          }}>
            {tab === 'stock' && (
              <>
                <StockSearchArea market={market} lang={lang} t={t} />
                <BreadthWidget market={market} t={t} />
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
                    period={period.value}
                    asOf={asOf}
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
                order={reOrder}
                retryKey={reRetryKey}
                onRetry={() => setReRetryKey((k) => k + 1)}
                onResetFilters={handleReResetFilters}
                onContentChange={setReHasContent}
                t={t}
              />
            )}
            {hasContent && (
              <AdFitUnit
                adUnit={import.meta.env.VITE_ADFIT_UNIT_DESKTOP_BOTTOM}
                width={300}
                height={250}
                style={{ margin: '16px auto' }}
              />
            )}
          </div>

          {tab === 'stock' && (
            <BacktestSidebar
              selected={selectedItem}
              btDetail={selectedItem != null ? getBtDetail(selectedItem.ticker) : emptyBtDetail}
              newsDetail={selectedItem != null ? getNews(selectedItem.ticker) : emptyNewsDetail}
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
      transition: 'background-color 0.25s ease',
    }}>
      <div style={{ width: '100%', maxWidth: 390, background: C.surface, minHeight: '100vh', display: 'flex', flexDirection: 'column', transition: 'background-color 0.25s ease' }}>
        <FomoHeader {...sharedControlProps} />

        {tab === 'stock' && (
          <>
            <StockSearchArea market={market} lang={lang} t={t} />
            <BreadthWidget market={market} t={t} />
            {status === 'loading' && <SkeletonList t={t} />}
            {status === 'empty' && <EmptyState t={t} onRetry={() => { handlePeriod(2); setCapTier('all') }} />}
            {status === 'error' && <ErrorState t={t} onRetry={() => setRetryKey((k) => k + 1)} />}
            {status === 'ok' && (
              <div style={{ padding: '12px 14px 16px', borderTop: `1px solid ${C.borderSub}`, flex: 1 }}>
                {asOf && (
                  <div style={{
                    fontSize: 11, color: C.textDim, fontFamily: FONT.mono,
                    marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    <span>{t.asOfLabel}</span>
                    <span style={{ color: C.textSub, fontWeight: 600 }}>{asOf}</span>
                  </div>
                )}
                {rankings.map((item) => (
                  <RankingCard
                    key={item.ticker}
                    item={item}
                    open={openRank === item.rank}
                    market={market}
                    days={period.days}
                    period={period.value}
                    btDetail={getBtDetail(item.ticker)}
                    newsDetail={getNews(item.ticker)}
                    lang={lang}
                    t={t}
                    onToggle={() => handleToggle(item.rank, item.ticker, item.has_news)}
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
            order={reOrder}
            retryKey={reRetryKey}
            onRetry={() => setReRetryKey((k) => k + 1)}
            onResetFilters={handleReResetFilters}
            onContentChange={setReHasContent}
            t={t}
          />
        )}

        {hasContent && (
          <AdFitUnit
            adUnit={import.meta.env.VITE_ADFIT_UNIT_MOBILE_BOTTOM}
            width={320}
            height={50}
            style={{ margin: '10px auto' }}
          />
        )}

        <Footer lang={lang} style={{ padding: '14px 16px 20px', borderTop: `1px solid ${C.borderSub}` }} />
      </div>
    </div>
  )
}
