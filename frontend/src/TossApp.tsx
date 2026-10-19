import { useCallback, useState } from 'react'
import { TossHeader } from './components/TossHeader'
import { RankingRow } from './components/RankingRow'
import { TossBanner } from './components/TossBanner'
import { BreadthWidget } from './components/BreadthWidget'
import { SkeletonList } from './components/SkeletonList'
import { EmptyState } from './components/EmptyState'
import { ErrorState } from './components/ErrorState'
import { useRankings } from './hooks/useRankings'
import { TOSS_COPY, TOSS_STR } from './i18n/strings.toss'
import { useC } from './ThemeContext'
import { KR_DOWN, KR_UP } from './tossColors'
import { PERIODS } from './types'
import { FONT } from './tokens'
import type { CapTier, Market, OrderDir } from './types'

const DEFAULT_PERIOD_IDX = 2 // 30d

/**
 * 앱인토스 미니앱 화면. 웹의 App.tsx와 별도 셸이라 백테스트·공유·부동산·뉴스·광고·글 등
 * 웹 전용 모듈을 import하지 않는다(그래서 번들에서 제외된다). 랭킹 조회는 웹과 같은 useRankings를 쓴다.
 */
export default function TossApp() {
  const C = useC()
  const t = TOSS_STR

  const [market, setMarket] = useState<Market>('kospi')
  const [periodIdx, setPeriodIdx] = useState(DEFAULT_PERIOD_IDX)
  const [capTier, setCapTier] = useState<CapTier>('all')
  const [order, setOrder] = useState<OrderDir>('desc')
  const [retryKey, setRetryKey] = useState(0)

  const period = PERIODS[periodIdx]!
  const { status, rankings, asOf } = useRankings(market, period.value, capTier, retryKey, order)

  const handleMarket = useCallback((m: Market) => {
    setCapTier('all')
    setMarket(m)
  }, [])

  return (
    <div style={{
      width: '100%', minHeight: '100vh', background: C.surface, fontFamily: FONT.sans,
      display: 'flex', flexDirection: 'column',
      paddingBottom: 'env(safe-area-inset-bottom)',
    }}>
      <TossHeader
        market={market}
        periodIdx={periodIdx}
        capTier={capTier}
        order={order}
        t={t}
        onMarket={handleMarket}
        onPeriod={setPeriodIdx}
        onCapTier={setCapTier}
        onOrder={setOrder}
      />
      <BreadthWidget market={market} t={t} upColor={KR_UP} downColor={KR_DOWN} />
      {status === 'loading' && <SkeletonList t={t} />}
      {status === 'empty' && <EmptyState t={t} onRetry={() => { setPeriodIdx(DEFAULT_PERIOD_IDX); setCapTier('all') }} />}
      {status === 'error' && <ErrorState t={t} onRetry={() => setRetryKey((k) => k + 1)} />}
      {status === 'ok' && (
        <div style={{ flex: 1 }}>
          {asOf && (
            <div style={{
              fontSize: 11, color: C.textDim, fontFamily: FONT.mono,
              padding: '10px 16px 4px', display: 'flex', gap: 6,
            }}>
              <span>{t.asOfLabel}</span>
              <span style={{ color: C.textSub, fontWeight: 600 }}>{asOf}</span>
              <span>{TOSS_COPY.closeNote}</span>
            </div>
          )}
          {rankings.map((item) => <RankingRow key={item.ticker} item={item} market={market} t={t} />)}
          {/* 광고는 스크롤되는 목록이 있을 때만, 목록 아래에 한 개만 둔다. */}
          <TossBanner />
        </div>
      )}
    </div>
  )
}
