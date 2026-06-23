import { apiFetch } from './client'
import type { Market, Period, RankingsResponse } from '../types'

export function fetchRankings(market: Market, period: Period, top = 10): Promise<RankingsResponse> {
  return apiFetch<RankingsResponse>('/api/rankings', { market, period, top })
}
