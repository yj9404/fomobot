import { useState, useCallback } from 'react'
import { fetchBacktest, asOfDate } from '../api/backtest'
import type { Market, Period, BacktestItem } from '../types'

type BtStatus = 'idle' | 'loading' | 'ok' | 'error'

interface BtEntry {
  status: BtStatus
  item: BacktestItem | null
}

export function useBacktest(market: Market, period: Period, days: number) {
  const [cache, setCache] = useState<Record<string, BtEntry>>({})

  const load = useCallback(
    async (ticker: string) => {
      const key = `${market}:${period}:${ticker}`
      if (cache[key]?.status === 'ok' || cache[key]?.status === 'loading') return

      setCache((prev) => ({ ...prev, [key]: { status: 'loading', item: null } }))

      try {
        const data = await fetchBacktest(market, asOfDate(days), period, 100)
        const found = data.items.find((i) => i.ticker === ticker) ?? null
        setCache((prev) => ({ ...prev, [key]: { status: 'ok', item: found } }))
      } catch {
        setCache((prev) => ({ ...prev, [key]: { status: 'error', item: null } }))
      }
    },
    [market, period, days, cache],
  )

  const get = useCallback(
    (ticker: string): BtEntry => {
      const key = `${market}:${period}:${ticker}`
      return cache[key] ?? { status: 'idle', item: null }
    },
    [market, period, cache],
  )

  return { load, get }
}
