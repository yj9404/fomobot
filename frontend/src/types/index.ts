export type Market = 'kospi' | 'nasdaq'
export type Period = '1d' | '7d' | '30d' | '90d' | '365d' | '1825d'
export type Lang = 'ko' | 'en'
export type Tab = 'stock' | 'realestate'
export type ReLevel = 'gu' | 'dong'
export type RealEstatePeriod = '3m' | '6m' | '1y' | '3y' | '5y' | '10y' | '20y'
export type DataStatus = 'ok' | 'insufficient' | 'no_start' | 'no_end'

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

export interface RePeriodDef {
  label: { ko: string; en: string }
  value: RealEstatePeriod
}

export const RE_PERIODS: RePeriodDef[] = [
  { label: { ko: '3개월', en: '3M'  }, value: '3m'  },
  { label: { ko: '6개월', en: '6M'  }, value: '6m'  },
  { label: { ko: '1년',   en: '1Y'  }, value: '1y'  },
  { label: { ko: '3년',   en: '3Y'  }, value: '3y'  },
  { label: { ko: '5년',   en: '5Y'  }, value: '5y'  },
  { label: { ko: '10년',  en: '10Y' }, value: '10y' },
  { label: { ko: '20년',  en: '20Y' }, value: '20y' },
]

export const RE_DISCLAIMER: Record<Lang, string> = {
  ko: '재미·교육 목적 · 과거 상승률이 미래 수익을 보장하지 않습니다',
  en: 'Educational only · Past gains do not guarantee future returns',
}

export const RE_REGIONS: { label: Record<Lang, string>; value: string }[] = [
  { label: { ko: '수도권 전체', en: 'All' }, value: '' },
  { label: { ko: '서울',       en: 'Seoul'  }, value: '11' },
  { label: { ko: '경기',       en: 'Gyeonggi' }, value: '41' },
  { label: { ko: '인천',       en: 'Incheon'  }, value: '28' },
]

// RE API response types — 단지(complex) 단위 랭킹
export interface ReRankingItem {
  complex_key: string
  apt_name: string
  display_name: string
  sigungu_code: string
  sigungu_name: string
  eupmyeondong: string
  rank: number | null
  change_pct: number | null
  start_ym: string
  end_ym: string
  start_price: number | null   // 만원/㎡
  end_price: number | null     // 만원/㎡
  start_deal_amount: number | null  // 만원, 중위 거래금액
  end_deal_amount: number | null    // 만원
  data_status: DataStatus
  start_tx_count: number | null
  end_tx_count: number | null
  insufficient_reason: string | null
}

export interface ReRankingsMeta {
  snapshot_ym: string
  period: RealEstatePeriod
  total_complexes: number
  is_recent_incomplete: boolean
  windows_overlap: boolean
  window_note: string | null
  recent_note: string
  disclaimer: string
}

export interface ReRankingsResponse {
  meta: ReRankingsMeta
  rankings: ReRankingItem[]
  excluded: ReRankingItem[]
}

// ── 주식 검색 / Quote ────────────────────────────────────────────────────
export interface SecurityItem {
  ticker: string
  name: string | null
  is_active: boolean
}

export interface StockSearchResponse {
  market: Market
  query: string
  results: SecurityItem[]
}

export interface DataCoverage {
  actual_start: string | null   // "YYYY-MM-DD"
  actual_end: string | null
  available_from: string | null
  trading_days: number
  warning: string | null
}

export interface StockQuoteResponse {
  ticker: string
  market: Market
  name: string | null
  start_date: string | null
  end_date: string | null
  start_price: number | null
  end_price: number | null
  return_pct: number | null
  mdd_pct: number | null
  volatility_annualized_pct: number | null
  data_coverage: DataCoverage
}

export const PERIODS: PeriodDef[] = [
  { label: { ko: '전일', en: '1D'  }, value: '1d',    days: 1    },
  { label: { ko: '7일', en: '7D'   }, value: '7d',    days: 7    },
  { label: { ko: '30일', en: '30D' }, value: '30d',   days: 30   },
  { label: { ko: '90일', en: '90D' }, value: '90d',   days: 90   },
  { label: { ko: '1년', en: '1Y'   }, value: '365d',  days: 365  },
  { label: { ko: '5년', en: '5Y'   }, value: '1825d', days: 1825 },
]
