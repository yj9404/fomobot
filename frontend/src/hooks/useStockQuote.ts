import { useState, useEffect } from 'react'
import { fetchStockQuote, fetchStockQuoteCustom } from '../api/stock'
import type { Market, Period, StockQuoteResponse } from '../types'

type QuoteState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; data: StockQuoteResponse }
  | { status: 'error'; msg: string }

export function useStockQuote(
  market: Market,
  ticker: string | null,
  period: Period | null,
  customStart?: string,
  customEnd?: string,
): QuoteState {
  const [state, setState] = useState<QuoteState>({ status: 'idle' })

  useEffect(() => {
    if (!ticker) {
      setState({ status: 'idle' })
      return
    }

    const useFixed = period != null && !customStart && !customEnd
    const useCustom = !period && !!customStart && !!customEnd

    if (!useFixed && !useCustom) {
      setState({ status: 'idle' })
      return
    }

    let cancelled = false
    setState({ status: 'loading' })

    const promise = useFixed
      ? fetchStockQuote(market, ticker, period!)
      : fetchStockQuoteCustom(market, ticker, customStart!, customEnd!)

    promise
      .then((data) => { if (!cancelled) setState({ status: 'ok', data }) })
      .catch((err: unknown) => {
        if (!cancelled) setState({ status: 'error', msg: err instanceof Error ? err.message : String(err) })
      })

    return () => { cancelled = true }
  }, [market, ticker, period, customStart, customEnd])

  return state
}
