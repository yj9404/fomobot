import { useState, useCallback, useRef } from 'react'
import { fetchBacktest, asOfDate } from '../api/backtest'
import type { Market, Period, BacktestItem, BacktestResponse } from '../types'

type BtStatus = 'idle' | 'loading' | 'ok' | 'error'

interface BtEntry {
  status: BtStatus
  item: BacktestItem | null
}

export function useBacktest(market: Market, period: Period, days: number) {
  const [cache, setCache] = useState<Record<string, BtEntry>>({})
  const inflight = useRef<Record<string, Promise<BacktestResponse>>>({})

  const load = useCallback(
    async (ticker: string) => {
      const key = `${market}:${period}:${ticker}`
      if (cache[key]?.status === 'ok' || cache[key]?.status === 'loading') return

      setCache((prev) => ({ ...prev, [key]: { status: 'loading', item: null } }))

      const reqKey = `${market}:${period}:${days}`

      if (!inflight.current[reqKey]) {
        const promise = fetchBacktest(market, asOfDate(days), period, 100)
        inflight.current[reqKey] = promise

        promise.catch(() => {}).finally(() => {
          if (inflight.current[reqKey] === promise) {
            delete inflight.current[reqKey]
          }
        })
      }

      try {
        const data = await inflight.current[reqKey]
        const found = data.items.find((i) => i.ticker === ticker) ?? null

        setCache((prev) => {
          const next = { ...prev }
          for (const item of data.items) {
            const itemKey = `${market}:${period}:${item.ticker}`
            next[itemKey] = { status: 'ok', item }
          }
          next[key] = { status: 'ok', item: found }
          return next
        })
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
