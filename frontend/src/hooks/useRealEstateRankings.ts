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

    fetchReRankings(period, sido || undefined)
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
  }, [period, sido, retryKey])

  return state
}
