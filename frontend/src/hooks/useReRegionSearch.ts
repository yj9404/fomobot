import { useState, useEffect, useRef } from 'react'
import { fetchReRegionSearch } from '../api/realestate'
import type { RegionItem } from '../types'

interface RegionSearchState {
  results: RegionItem[]
  loading: boolean
}

export function useReRegionSearch(q: string): RegionSearchState {
  const [state, setState] = useState<RegionSearchState>({ results: [], loading: false })
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!q.trim()) {
      setState({ results: [], loading: false })
      return
    }

    setState((s) => ({ ...s, loading: true }))
    if (timerRef.current) clearTimeout(timerRef.current)

    timerRef.current = setTimeout(() => {
      fetchReRegionSearch(q)
        .then((data) => setState({ results: data.results, loading: false }))
        .catch(() => setState({ results: [], loading: false }))
    }, 300)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [q])

  return state
}
