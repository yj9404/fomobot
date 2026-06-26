import { apiFetch } from './client'
import type { ReLevel, RealEstatePeriod, ReRankingsResponse } from '../types'

export function fetchReRankings(
  level: ReLevel,
  period: RealEstatePeriod,
  region?: string,
  top = 20,
): Promise<ReRankingsResponse> {
  const params: Record<string, string | number> = { level, period, top }
  if (region) params.region = region
  return apiFetch<ReRankingsResponse>('/api/realestate/rankings', params)
}
