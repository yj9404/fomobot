import { useState, useEffect } from 'react'
import { fetchRankings } from '../api/rankings'
import type { CapTier, Market, Period, RankingItem } from '../types'

type Status = 'loading' | 'ok' | 'empty' | 'error'

interface RankingsState {
  status: Status
  rankings: RankingItem[]
  disclaimer: string
  errorMsg: string
}

export function useRankings(market: Market, period: Period, capTier: CapTier, retryKey: number = 0) {
  const [state, setState] = useState<RankingsState>({
    status: 'loading',
    rankings: [],
    disclaimer: '',
    errorMsg: '',
  })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading', rankings: [], disclaimer: '', errorMsg: '' })

    fetchRankings(market, period, capTier)
      .then((data) => {
        if (cancelled) return
        if (data.rankings.length === 0) {
          setState({ status: 'empty', rankings: [], disclaimer: data.disclaimer, errorMsg: '' })
        } else {
          setState({ status: 'ok', rankings: data.rankings, disclaimer: data.disclaimer, errorMsg: '' })
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : String(err)
        console.error('[useRankings]', msg)
        setState({
          status: 'error',
          rankings: [],
          disclaimer: '',
          errorMsg: msg,
        })
      })

    return () => { cancelled = true }
  }, [market, period, capTier, retryKey])

  return state
}
