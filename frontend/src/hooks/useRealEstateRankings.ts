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
  sido: string,       // 시도 필터 ('11'=서울, '28'=인천, '41'=경기, ''=수도권 전체)
  retryKey: number = 0,
  gu?: string,        // 5자리 시군구 코드 (sido보다 좁은 필터)
  dong?: string,      // 법정동명 부분일치
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

    // gu가 설정되면 sido 대신 gu로 필터 (gu가 더 좁음)
    const sidoParam = gu ? undefined : (sido || undefined)
    fetchReRankings(period, sidoParam, gu || undefined, dong || undefined)
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
  }, [period, sido, gu, dong, retryKey])

  return state
}
