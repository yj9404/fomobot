import { useState, useEffect } from 'react'
import { fetchRankings } from '../api/rankings'
import type { CapTier, Market, OrderDir, Period, RankingItem } from '../types'

type Status = 'loading' | 'ok' | 'empty' | 'error'

interface RankingsState {
  status: Status
  rankings: RankingItem[]
  disclaimer: string
  errorMsg: string
  asOf: string
}

export function useRankings(market: Market, period: Period, capTier: CapTier, retryKey: number = 0, order: OrderDir = 'desc') {
  const [state, setState] = useState<RankingsState>({
    status: 'loading',
    rankings: [],
    disclaimer: '',
    errorMsg: '',
    asOf: '',
  })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading', rankings: [], disclaimer: '', errorMsg: '', asOf: '' })

    fetchRankings(market, period, capTier, 20, order)
      .then((data) => {
        if (cancelled) return
        if (data.rankings.length === 0) {
          setState({ status: 'empty', rankings: [], disclaimer: data.disclaimer, errorMsg: '', asOf: data.as_of })
        } else {
          setState({ status: 'ok', rankings: data.rankings, disclaimer: data.disclaimer, errorMsg: '', asOf: data.as_of })
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
          asOf: '',
        })
      })

    return () => { cancelled = true }
  }, [market, period, capTier, retryKey, order])

  return state
}
