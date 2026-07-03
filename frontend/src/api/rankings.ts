import { apiFetch } from './client'
import type { CapTier, Market, OrderDir, Period, RankingsResponse } from '../types'

export function fetchRankings(market: Market, period: Period, capTier: CapTier = 'all', top = 20, order: OrderDir = 'desc'): Promise<RankingsResponse> {
  return apiFetch<RankingsResponse>('/api/stock/rankings', { market, period, cap_tier: capTier, top, order })
}
