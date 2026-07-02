import { apiFetch } from './client'
import type {
  RealEstatePeriod,
  ReRankingsResponse,
  RegionSearchResponse,
  ReSearchResponse,
  SegmentsResponse,
} from '../types'

export function fetchReRankings(
  period: RealEstatePeriod,
  sido?: string,   // 시도 필터: 11=서울, 28=인천, 41=경기
  gu?: string,     // 5자리 시군구 코드
  dong?: string,   // 법정동명 부분일치
  top = 20,
  seg?: string,    // 학군 세그먼트 키 (지정 시 sido/gu/dong 무시)
): Promise<ReRankingsResponse> {
  const params: Record<string, string | number> = { period, top }
  if (seg) {
    params.seg = seg
  } else {
    if (sido) params.sido = sido
    if (gu) params.gu = gu
    if (dong) params.dong = dong
  }
  return apiFetch<ReRankingsResponse>('/api/realestate/rankings', params)
}

export function fetchReRegionSearch(q: string): Promise<RegionSearchResponse> {
  return apiFetch<RegionSearchResponse>('/api/realestate/regions', { q })
}

export function fetchReAptSearch(
  q: string,
  period: RealEstatePeriod,
  gu?: string,
  dong?: string,
): Promise<ReSearchResponse> {
  const params: Record<string, string> = { q, period }
  if (gu) params.gu = gu
  if (dong) params.dong = dong
  return apiFetch<ReSearchResponse>('/api/realestate/search', params)
}

export function fetchReSegments(): Promise<SegmentsResponse> {
  return apiFetch<SegmentsResponse>('/api/realestate/segments', {})
}
