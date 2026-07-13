import { apiFetch, ApiError } from './client'
import type { BreadthResponse, Market } from '../types'

/** 데이터 없음(404)은 정상적인 "빈 상태"이므로 null을 반환한다(에러 아님). */
export async function fetchBreadth(market: Market): Promise<BreadthResponse | null> {
  try {
    return await apiFetch<BreadthResponse>('/api/breadth', { market })
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}
