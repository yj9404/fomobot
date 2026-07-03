import { useState, useEffect } from 'react'
import { fetchReRankings } from '../api/realestate'
import type { RealEstatePeriod, ReRankingItem, ReRankingsMeta } from '../types'

type Status = 'loading' | 'ok' | 'empty' | 'error'

export interface ReRankingsState {
  status: Status
  rankings: ReRankingItem[]
  excluded: ReRankingItem[]
  meta: ReRankingsMeta | null
}

export function useRealEstateRankings(
  period: RealEstatePeriod,
  sido: string,          // 시도 필터 ('11'=서울, '28'=인천, '41'=경기, ''=수도권 전체)
  retryKey: number = 0,
  gu?: string,           // 5자리 시군구 코드 (sido보다 좁은 필터)
  dong?: string,         // 법정동명 부분일치
  seg?: string,          // 학군 세그먼트 키 (지정 시 sido/gu/dong 무시)
  minPrice?: number | null,  // 84㎡ 환산 금액 하한 (억 단위)
  maxPrice?: number | null,  // 84㎡ 환산 금액 상한 (억 단위)
): ReRankingsState {
  const [state, setState] = useState<ReRankingsState>({
    status: 'loading',
    rankings: [],
    excluded: [],
    meta: null,
  })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading', rankings: [], excluded: [], meta: null })

    // seg 있으면 sido/gu/dong 모두 무시 (백엔드와 동일 규칙)
    const sidoParam = seg ? undefined : (gu ? undefined : (sido || undefined))
    const guParam   = seg ? undefined : (gu || undefined)
    const dongParam = seg ? undefined : (dong || undefined)
    const segParam  = seg || undefined

    fetchReRankings(
      period, sidoParam, guParam, dongParam, 20, segParam,
      minPrice ?? undefined, maxPrice ?? undefined,
    )
      .then((data) => {
        if (cancelled) return
        if (data.rankings.length === 0 && data.excluded.length === 0) {
          setState({ status: 'empty', rankings: [], excluded: [], meta: data.meta })
        } else {
          setState({ status: 'ok', rankings: data.rankings, excluded: data.excluded, meta: data.meta })
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        console.error('[useRealEstateRankings]', err)
        setState({ status: 'error', rankings: [], excluded: [], meta: null })
      })

    return () => { cancelled = true }
  }, [period, sido, gu, dong, seg, minPrice, maxPrice, retryKey])

  return state
}
