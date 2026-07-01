import { apiFetch } from './client'
import type { Market, Period, BacktestResponse } from '../types'

export function fetchBacktest(
  market: Market,
  asOf: string,
  period: Period,
  top = 10,
): Promise<BacktestResponse> {
  return apiFetch<BacktestResponse>('/api/stock/backtest', { market, as_of: asOf, period, top })
}

export function asOfDate(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
