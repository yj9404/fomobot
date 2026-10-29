import { Fragment, useEffect, useState } from 'react'
import { TossHeader } from '../components/TossHeader'
import { RankingRow } from '../components/RankingRow'
import { TossBanner } from '../components/TossBanner'
import { BreadthWidget } from '../components/BreadthWidget'
import { SkeletonList } from '../components/SkeletonList'
import { EmptyState } from '../components/EmptyState'
import { ErrorState } from '../components/ErrorState'
import { useRankings } from '../hooks/useRankings'
import { TOSS_STR, TOSS_UI } from '../i18n/strings.toss'
import { useC } from '../ThemeContext'
import { KR_DOWN, KR_UP } from '../tossColors'
import { PERIODS } from '../types'
import { FONT } from '../tokens'
import type { Market } from '../types'
import { useRestoreScroll, useRouter } from './router'
import { DEFAULT_RANKINGS, stockRoute, type RankingsRoute } from './routes'
import { ShareAction } from './ShareAction'
import { AdFreePass } from './AdFreePass'
import { preloadDetailInterstitial, withDetailInterstitial } from './ads'

const BANNER_AFTER_INDEX = 4 // 5번째 행 아래

/**
 * 순위 화면(앱 첫 화면). 시장·기간·시총·정렬은 URL(hash)에 두어 뒤로가기로 돌아와도,
 * 공유 링크로 들어와도 같은 조건이 복원된다.
 */
export function RankingsScreen({ route }: { route: RankingsRoute }) {
  const C = useC()
  const t = TOSS_STR
  const { replace, push } = useRouter()
  const [retryKey, setRetryKey] = useState(0)

  const { market, period, cap, order } = route
  const periodIdx = Math.max(0, PERIODS.findIndex((p) => p.value === period))
  const { status, rankings, asOf } = useRankings(market, period, cap, retryKey, order)
  useRestoreScroll(status === 'ok')
  useEffect(preloadDetailInterstitial, [])

  const update = (patch: Partial<RankingsRoute>) => replace({ ...route, ...patch })

  return (
    <>
      <TossHeader
        market={market}
        periodIdx={periodIdx}
        capTier={cap}
        order={order}
        t={t}
        onSearch={() => push({ name: 'search', q: '' })}
        onMarket={(m: Market) => update({ market: m, cap: 'all' })}
        onPeriod={(i) => update({ period: PERIODS[i]!.value })}
        onCapTier={(c) => update({ cap: c })}
        onOrder={(o) => update({ order: o })}
      />
      <BreadthWidget market={market} t={t} upColor={KR_UP} downColor={KR_DOWN} />
      <AdFreePass />
      {status === 'loading' && <SkeletonList t={t} />}
      {status === 'empty' && <EmptyState t={t} onRetry={() => update({ period: DEFAULT_RANKINGS.period, cap: 'all' })} />}
      {status === 'error' && <ErrorState t={t} onRetry={() => setRetryKey((k) => k + 1)} />}
      {status === 'ok' && (
        <div style={{ flex: 1 }}>
          {asOf && (
            <div style={{
              fontSize: 11, color: C.textDim, fontFamily: FONT.mono,
              padding: '6px 16px 4px', display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <span>{t.asOfLabel}</span>
              <span style={{ color: C.textSub, fontWeight: 600 }}>{asOf}</span>
              <span>{t.closeNote}</span>
              <ShareAction
                compact
                route={route}
                asOf={asOf}
                message={TOSS_UI.rankingsShareMessage(market.toUpperCase(), PERIODS[periodIdx]!.label.ko, TOSS_UI.orderShort[order])}
              />
            </div>
          )}
          {rankings.map((item, i) => (
            <Fragment key={item.ticker}>
              <RankingRow item={item} market={market} t={t} onClick={() => withDetailInterstitial(() => push(stockRoute(market, item.ticker)))} />
              {/* 광고는 한 화면에 한 개만. 목록 중간(5위 아래)에 두고, 이후 행이 더 있어 스크롤되는 경우에만 넣는다. */}
              {i === BANNER_AFTER_INDEX && rankings.length > BANNER_AFTER_INDEX + 1 && <TossBanner />}
            </Fragment>
          ))}
        </div>
      )}
    </>
  )
}
