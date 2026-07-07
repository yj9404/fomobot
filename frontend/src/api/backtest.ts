import { apiFetch } from './client'
import type { Market, Period, BacktestResponse, BacktestDetailResponse } from '../types'

export function fetchBacktest(
  market: Market,
  asOf: string,
  period: Period,
  top = 10,
): Promise<BacktestResponse> {
  return apiFetch<BacktestResponse>('/api/stock/backtest', { market, as_of: asOf, period, top })
}

export function fetchBacktestDetail(
  market: Market,
  ticker: string,
  asOf: string,
  period: Period,
): Promise<BacktestDetailResponse> {
  return apiFetch<BacktestDetailResponse>('/api/stock/backtest/detail', {
    market,
    ticker,
    as_of: asOf,
    period,
  })
}
