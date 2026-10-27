import { useEffect, useState } from 'react'
import { ApiError, apiFetch } from '../api/client'
import type { Market, Period } from '../types'

/** backend GET /api/stock/detail (schemas/stock_detail.py) */
export interface PeriodChange {
  change_pct: number
  start_date: string
  end_date: string
}

export interface StockDetail {
  market: Market
  ticker: string
  name: string
  is_active: boolean
  status: 'ok' | 'correcting' | 'no_data'
  as_of: string | null
  close: number | null
  close_date: string | null
  changes: Record<Period, PeriodChange | null>
  series: [string, number][]
}

export type DetailState =
  | { status: 'loading' }
  | { status: 'ok'; data: StockDetail }
  | { status: 'not_found' }
  | { status: 'error' }

export function useStockDetail(market: Market, ticker: string, retryKey: number): DetailState {
  const [state, setState] = useState<DetailState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    apiFetch<StockDetail>('/api/stock/detail', { market, ticker })
      .then((data) => { if (!cancelled) setState({ status: 'ok', data }) })
      .catch((err: unknown) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 404) setState({ status: 'not_found' })
        else {
          console.error('[useStockDetail]', err)
          setState({ status: 'error' })
        }
      })
    return () => { cancelled = true }
  }, [market, ticker, retryKey])

  return state
}
