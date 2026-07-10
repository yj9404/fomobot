import { apiFetch } from './client'
import type {
  OrderDir,
  RealEstatePeriod,
  ReRankingsResponse,
  RegionSearchResponse,
  ReSearchResponse,
  SegmentsResponse,
  NewsArticle,
  NewsResponse,
} from '../types'

export function fetchReRankings(
  period: RealEstatePeriod,
  sido?: string,        // 시도 필터: 11=서울, 28=인천, 41=경기
  gu?: string,          // 5자리 시군구 코드
  dong?: string,        // 법정동명 부분일치
  top = 20,
  seg?: string,         // 학군 세그먼트 키 (지정 시 sido/gu/dong 무시)
  minPrice?: number,    // 84㎡ 환산 금액 하한 (억 단위, 이상 ≥)
  maxPrice?: number,    // 84㎡ 환산 금액 상한 (억 단위, 이하 ≤)
  order: OrderDir = 'desc',
): Promise<ReRankingsResponse> {
  const params: Record<string, string | number> = { period, top, order }
  if (seg) {
    params.seg = seg
  } else {
    if (sido) params.sido = sido
    if (gu) params.gu = gu
    if (dong) params.dong = dong
  }
  if (minPrice != null) params.min_price = minPrice
  if (maxPrice != null) params.max_price = maxPrice
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

/** 클릭/펼침 시에만 호출 — 리스트 로드 시 미리 fetch하지 않는다. */
export function fetchReComplexNews(complexKey: string): Promise<NewsArticle[]> {
  return apiFetch<NewsResponse>(`/api/realestate/news/${encodeURIComponent(complexKey)}`, {}).then((r) => r.articles)
}
