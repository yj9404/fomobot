import { apiFetch } from './client'
import type { Market, Period, RankingsResponse } from '../types'

export function fetchRankings(market: Market, period: Period, top = 10): Promise<RankingsResponse> {
  return apiFetch<RankingsResponse>('/api/stock/rankings', { market, period, top })
}
