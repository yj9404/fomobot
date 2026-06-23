export type Market = 'kospi' | 'nasdaq'
export type Period = '1d' | '7d' | '30d' | '90d' | '365d' | '1825d'
export type Lang = 'ko' | 'en'

export interface RankingItem {
  rank: number
  ticker: string
  name: string | null
  return_pct: number
  mdd_pct: number | null
  volatility_annualized_pct: number | null
  excess_return_vs_index_pct: number | null
}

export interface RankingsResponse {
  disclaimer: string
  market: Market
  period: Period
  as_of: string
  top: number
  rankings: RankingItem[]
}

export interface BacktestItem {
  rank_at_as_of: number
  ticker: string
  name: string | null
  return_pct_at_as_of: number
  current_return_pct: number | null
}

export interface BacktestResponse {
  market: Market
  period: Period
  as_of: string
  top: number
  avg_current_return_pct: number | null
  survival_bias_warning?: string
  items: BacktestItem[]
}

export interface PeriodDef {
  label: { ko: string; en: string }
  value: Period
  days: number
}

export const PERIODS: PeriodDef[] = [
  { label: { ko: '전일', en: '1D'  }, value: '1d',    days: 1    },
  { label: { ko: '7일', en: '7D'   }, value: '7d',    days: 7    },
  { label: { ko: '30일', en: '30D' }, value: '30d',   days: 30   },
  { label: { ko: '90일', en: '90D' }, value: '90d',   days: 90   },
  { label: { ko: '1년', en: '1Y'   }, value: '365d',  days: 365  },
  { label: { ko: '5년', en: '5Y'   }, value: '1825d', days: 1825 },
]
