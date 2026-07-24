import { client } from './client'
import type { Market, Period, BacktestResponse, BacktestDetailResponse } from '../types'

export function fetchBacktest(
  market: Market,
  asOf: string,
  period: Period,
  top: number = 20
): Promise<BacktestResponse> {
  return client.get<BacktestResponse>('/api/stock/backtest', {
    market,
    as_of: asOf,
    period,
    top: top.toString(),
  });
}

export function fetchBacktestDetail(
  market: Market,
  ticker: string,
  asOf: string,
  period: Period,
): Promise<BacktestDetailResponse> {
  return client.get<BacktestDetailResponse>('/api/stock/backtest/detail', {
    market,
    ticker,
    as_of: asOf,
    period,
  })
}
