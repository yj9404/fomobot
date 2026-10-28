import { useEffect, useState } from 'react'
import { ApiError, apiFetch } from '../api/client'
import type { Market, Period } from '../types'

/** backend GET /api/stock/detail (schemas/stock_detail.py) */
export interface PeriodChange {
  change_pct: number
  start_date: string
  end_date: string
}

export interface StockDetail {
  market: Market
  ticker: string
  name: string
  is_active: boolean
  status: 'ok' | 'correcting' | 'no_data'
  as_of: string | null
  close: number | null
  close_date: string | null
  changes: Record<Period, PeriodChange | null>
  series: [string, number][]
}

export type DetailState =
  | { status: 'loading' }
  | { status: 'ok'; data: StockDetail }
  | { status: 'not_found' }
  | { status: 'error' }

export function useStockDetail(market: Market, ticker: string, retryKey: number): DetailState {
  const [state, setState] = useState<DetailState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    setState({ status: 'loading' })
    apiFetch<StockDetail>('/api/stock/detail', { market, ticker })
      .then((data) => { if (!cancelled) setState({ status: 'ok', data }) })
      .catch((err: unknown) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 404) setState({ status: 'not_found' })
        else {
          console.error('[useStockDetail]', err)
          setState({ status: 'error' })
        }
      })
    return () => { cancelled = true }
  }, [market, ticker, retryKey])

  return state
}

/** backend GET /api/stock/news/{ticker}/toss (schemas/news.py TossNewsArticle) */
export interface TossNewsArticle {
  title: string
  source: string
  url: string
  published_at: string
}

/**
 * 종목 뉴스. 불러오는 중·실패·0건을 구분하지 않고 빈 배열을 준다 — 화면은 뉴스가 있을 때만 섹션을 그린다.
 * ticker가 null이면 요청하지 않는다(뉴스는 KOSPI 랭킹 종목만 수집되므로 그 밖에는 부르지 않는다).
 */
export function useStockNews(ticker: string | null): TossNewsArticle[] {
  const [articles, setArticles] = useState<TossNewsArticle[]>([])

  useEffect(() => {
    setArticles([])
    if (!ticker) return
    let cancelled = false
    apiFetch<{ articles: TossNewsArticle[] }>(`/api/stock/news/${encodeURIComponent(ticker)}/toss`, {})
      .then((r) => { if (!cancelled) setArticles(r.articles) })
      .catch((err: unknown) => console.error('[useStockNews]', err))
    return () => { cancelled = true }
  }, [ticker])

  return articles
}
