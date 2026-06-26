import { apiFetch } from './client'
import type { RealEstatePeriod, ReRankingsResponse } from '../types'

export function fetchReRankings(
  period: RealEstatePeriod,
  sido?: string,   // 시도 필터: 11=서울, 28=인천, 41=경기. 미지정 시 수도권 전체
  top = 20,
): Promise<ReRankingsResponse> {
  const params: Record<string, string | number> = { period, top }
  if (sido) params.sido = sido
  return apiFetch<ReRankingsResponse>('/api/realestate/rankings', params)
}
