import { useState, useEffect, useRef } from 'react'
import { fetchStockSearch } from '../api/stock'
import type { Market, SecurityItem } from '../types'

interface SearchState {
  results: SecurityItem[]
  loading: boolean
}

export function useStockSearch(market: Market, q: string): SearchState {
  const [state, setState] = useState<SearchState>({ results: [], loading: false })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!q.trim()) {
      setState({ results: [], loading: false })
      return
    }

    setState((s) => ({ ...s, loading: true }))
    if (timerRef.current) clearTimeout(timerRef.current)

    timerRef.current = setTimeout(() => {
      fetchStockSearch(market, q)
        .then((data) => setState({ results: data.results, loading: false }))
        .catch(() => setState({ results: [], loading: false }))
    }, 300)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [market, q])

  return state
}
