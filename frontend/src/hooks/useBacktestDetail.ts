import { useState, useCallback } from 'react'
import { fetchBacktestDetail } from '../api/backtest'
import type { Market, Period, BacktestDetailResponse } from '../types'

type BtStatus = 'idle' | 'loading' | 'ok' | 'error'

interface BtDetailEntry {
  status: BtStatus
  detail: BacktestDetailResponse | null
}

/**
 * asOf: 랭킹 카드가 쓰는 것과 동일한 기준일(useRankings().asOf)을 그대로 받는다.
 * useBacktest(목록 기반)와 동일한 캐시 패턴이지만, 종목 하나의 상세
 * (equity_curve 포함)를 /api/stock/backtest/detail에서 직접 받아온다.
 */
export function useBacktestDetail(market: Market, period: Period, asOf: string) {
  const [cache, setCache] = useState<Record<string, BtDetailEntry>>({})

  const load = useCallback(
    async (ticker: string) => {
      if (!asOf) return
      const key = `${market}:${period}:${asOf}:${ticker}`
      if (cache[key]?.status === 'ok' || cache[key]?.status === 'loading') return

      setCache((prev) => ({ ...prev, [key]: { status: 'loading', detail: null } }))

      try {
        const data = await fetchBacktestDetail(market, ticker, asOf, period)
        setCache((prev) => ({ ...prev, [key]: { status: 'ok', detail: data } }))
      } catch {
        setCache((prev) => ({ ...prev, [key]: { status: 'error', detail: null } }))
      }
    },
    [market, period, asOf, cache],
  )

  const get = useCallback(
    (ticker: string): BtDetailEntry => {
      const key = `${market}:${period}:${asOf}:${ticker}`
      return cache[key] ?? { status: 'idle', detail: null }
    },
    [market, period, asOf, cache],
  )

  return { load, get }
}
