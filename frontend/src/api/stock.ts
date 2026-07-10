import { apiFetch } from './client'
import type { Market, Period, StockSearchResponse, StockQuoteResponse, StockDateBoundsResponse, NewsArticle, NewsResponse } from '../types'

export function fetchStockDateBounds(market: Market): Promise<StockDateBoundsResponse> {
  return apiFetch<StockDateBoundsResponse>('/api/stock/date-bounds', { market })
}

export function fetchStockSearch(market: Market, q: string): Promise<StockSearchResponse> {
  return apiFetch<StockSearchResponse>('/api/stock/search', { market, q })
}

export function fetchStockQuote(
  market: Market,
  ticker: string,
  period: Period,
): Promise<StockQuoteResponse> {
  return apiFetch<StockQuoteResponse>('/api/stock/quote', { market, ticker, period })
}

export function fetchStockQuoteCustom(
  market: Market,
  ticker: string,
  start: string,
  end: string,
): Promise<StockQuoteResponse> {
  return apiFetch<StockQuoteResponse>('/api/stock/quote', { market, ticker, start, end })
}

/** 클릭/펼침 시에만 호출 — 리스트 로드 시 미리 fetch하지 않는다. */
export function fetchStockNews(ticker: string): Promise<NewsArticle[]> {
  return apiFetch<NewsResponse>(`/api/stock/news/${encodeURIComponent(ticker)}`, {}).then((r) => r.articles)
}
