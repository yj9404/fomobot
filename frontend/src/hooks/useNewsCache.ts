import { useState, useCallback } from 'react'
import type { NewsArticle } from '../types'

type NewsStatus = 'idle' | 'loading' | 'ok' | 'error'

export interface NewsEntry {
  status: NewsStatus
  articles: NewsArticle[]
}

const IDLE_ENTRY: NewsEntry = { status: 'idle', articles: [] }

/**
 * 대상(ticker/complex_key) id 하나로 키를 잡는 뉴스 캐시.
 * useBacktestDetail과 동일한 가드(이미 ok/loading이면 재요청 안 함)로
 * 같은 항목 재펼침 시 중복 fetch를 막는다.
 *
 * 뉴스는 백엔드에서 배치가 미리 채워둔 값이라 기간(period)/기준일(asOf)에
 * 안 묶이므로 id 단일 키로 충분하다.
 */
export function useNewsCache(fetchFn: (id: string) => Promise<NewsArticle[]>) {
  const [cache, setCache] = useState<Record<string, NewsEntry>>({})

  const load = useCallback(
    async (id: string) => {
      if (cache[id]?.status === 'ok' || cache[id]?.status === 'loading') return

      setCache((prev) => ({ ...prev, [id]: { status: 'loading', articles: [] } }))

      try {
        const articles = await fetchFn(id)
        setCache((prev) => ({ ...prev, [id]: { status: 'ok', articles } }))
      } catch {
        setCache((prev) => ({ ...prev, [id]: { status: 'error', articles: [] } }))
      }
    },
    [cache, fetchFn],
  )

  const get = useCallback((id: string): NewsEntry => cache[id] ?? IDLE_ENTRY, [cache])

  return { load, get }
}
