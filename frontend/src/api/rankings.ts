import { apiFetch } from './client'
import type { CapTier, Market, Period, RankingsResponse } from '../types'

export function fetchRankings(market: Market, period: Period, capTier: CapTier = 'all', top = 10): Promise<RankingsResponse> {
  return apiFetch<RankingsResponse>('/api/stock/rankings', { market, period, cap_tier: capTier, top })
}
