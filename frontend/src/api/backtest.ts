import { apiFetch } from './client'
import type { Market, Period, BacktestResponse } from '../types'

export function fetchBacktest(
  market: Market,
  asOf: string,
  period: Period,
  top = 10,
): Promise<BacktestResponse> {
  return apiFetch<BacktestResponse>('/api/backtest', { market, as_of: asOf, period, top })
}

export function asOfDate(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}
