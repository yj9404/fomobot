import { useState, useCallback } from 'react'
import { FomoHeader } from './components/FomoHeader'
import { RankingCard } from './components/RankingCard'
import { SkeletonList } from './components/SkeletonList'
import { EmptyState } from './components/EmptyState'
import { ErrorState } from './components/ErrorState'
import { useRankings } from './hooks/useRankings'
import { useBacktest } from './hooks/useBacktest'
import { useStrings } from './i18n/strings'
import { PERIODS } from './types'
import { C, FONT } from './tokens'
import type { Lang, Market } from './types'

export default function App() {
  const [lang, setLang] = useState<Lang>('ko')
  const [market, setMarket] = useState<Market>('kospi')
  const [periodIdx, setPeriodIdx] = useState(2) // default: 30d
  const [openRank, setOpenRank] = useState<number | null>(null)
  const [retryKey, setRetryKey] = useState(0)

  const t = useStrings(lang)
  const period = PERIODS[periodIdx]!
  const { status, rankings, disclaimer, errorMsg } = useRankings(market, period.value, retryKey)
  const { load: loadBt, get: getBt } = useBacktest(market, period.value, period.days)

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

  const handleMarket = useCallback((m: Market) => {
    setOpenRank(null)
    setMarket(m)
  }, [])

  const handlePeriod = useCallback((i: number) => {
    setOpenRank(null)
    setPeriodIdx(i)
  }, [])

  return (
    <div style={{
      minWidth: '100%',
      minHeight: '100vh',
      background: C.bg,
      display: 'flex',
      justifyContent: 'center',
      fontFamily: FONT.sans,
    }}>
      <div style={{ width: '100%', maxWidth: 390, background: C.surface, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <FomoHeader
          lang={lang}
          market={market}
          periodIdx={periodIdx}
          disclaimer={disclaimer}
          t={t}
          onLang={setLang}
          onMarket={handleMarket}
          onPeriod={handlePeriod}
        />

        {status === 'loading' && <SkeletonList t={t} />}

        {status === 'empty' && <EmptyState t={t} onRetry={() => handlePeriod(2)} />}

        {status === 'error' && <ErrorState t={t} errorMsg={errorMsg} onRetry={() => setRetryKey((k) => k + 1)} />}

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
      </div>
    </div>
  )
}
