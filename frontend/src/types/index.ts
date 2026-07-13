export type Market = 'kospi' | 'nasdaq'
export type Period = '1d' | '7d' | '30d' | '90d' | '365d' | '1825d'
export type Lang = 'ko' | 'en'
export type Tab = 'stock' | 'realestate'
export type RealEstatePeriod = '3m' | '6m' | '1y' | '3y' | '5y' | '10y' | '20y'
export type DataStatus = 'ok' | 'insufficient' | 'no_start' | 'no_end'
export type CapTier = 'all' | 'small' | 'mid' | 'large'
export type OrderDir = 'desc' | 'asc'

export interface RankingItem {
  rank: number
  ticker: string
  name: string | null
  return_pct: number
  mdd_pct: number | null
  volatility_annualized_pct: number | null
  excess_return_vs_index_pct: number | null
  has_news?: boolean | null
}

export interface RankingsResponse {
  disclaimer: string
  market: Market
  period: Period
  as_of: string
  top: number
  order: OrderDir
  rankings: RankingItem[]
}

export interface ScenarioResult {
  final_return_pct: number
  mdd_pct: number | null
  warning: string | null
  executed_installments: number | null
  total_installments: number | null
}

export interface BacktestScenarios {
  buy_and_hold: ScenarioResult | null
  dca: ScenarioResult | null
}

export interface BacktestItem {
  rank_at_as_of: number
  ticker: string
  name: string | null
  return_pct_at_as_of: number
  scenarios: BacktestScenarios
}

export interface BacktestResponse {
  market: Market
  period: Period
  as_of: string
  top: number
  avg_buy_and_hold_return_pct: number | null
  survival_bias_warning?: string
  items: BacktestItem[]
}

export interface EquityPoint {
  date: string
  value: number
}

export interface ScenarioDetail extends ScenarioResult {
  equity_curve: EquityPoint[]
}

export interface BacktestDetailScenarios {
  buy_and_hold: ScenarioDetail | null
  dca: ScenarioDetail | null
}

export interface BacktestDetailResponse {
  market: Market
  ticker: string
  name: string | null
  period: Period
  as_of: string
  actual_as_of: string
  principal: number
  first_traded_date: string | null
  survival_bias_warning?: string
  scenarios: BacktestDetailScenarios
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
  ko: '투자 조언이 아닙니다. FomoBot은 지나간 걸 보여줄 뿐이에요',
  en: 'Not financial advice · FomoBot just shows what already happened',
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
  has_news?: boolean | null
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
  order: OrderDir
}

export interface ReRankingsResponse {
  meta: ReRankingsMeta
  rankings: ReRankingItem[]
  excluded: ReRankingItem[]
}

// ── 부동산 세그먼트 타입 ─────────────────────────────────────────────────
export interface SegmentItem {
  seg_key: string
  label: string
  description: string
}

export interface SegmentsResponse {
  segments: SegmentItem[]
}

// ── 부동산 검색 타입 ─────────────────────────────────────────────────────
export type SearchDataStatus = 'ok' | 'insufficient' | 'no_start' | 'no_end' | 'no_snapshot'

export interface RegionItem {
  sido_code: string        // 앞 2자리 (11/28/41)
  sido_name: string        // 서울/인천/경기
  sigungu_code: string     // 5자리 — rankings gu= 파라미터에 그대로 사용
  sigungu_name: string
  eupmyeondong: string
}

export interface RegionSearchResponse {
  query: string
  results: RegionItem[]
}

export interface ReSearchResultItem {
  complex_key: string
  apt_name: string
  display_name: string | null
  sigungu_code: string
  sigungu_name: string | null
  eupmyeondong: string
  rank: number | null
  change_pct: number | null
  start_price: number | null        // 만원/㎡
  end_price: number | null          // 만원/㎡
  start_deal_amount: number | null  // 만원, 중위 거래금액
  end_deal_amount: number | null
  start_tx_count: number | null
  end_tx_count: number | null
  start_ym: string | null
  end_ym: string | null
  data_status: SearchDataStatus
  insufficient_reason: string | null
}

export interface ReSearchResponse {
  query: string
  period: string
  snapshot_ym: string | null
  results: ReSearchResultItem[]
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

export interface StockDateBoundsResponse {
  market: Market
  min_date: string | null
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

// ── 시장 breadth (상승/하락/보합 종목 수) ───────────────────────────────────
export interface BreadthResponse {
  market: Market
  date: string
  advancers: number
  decliners: number
  unchanged: number
  excluded: number
  halted: number
  total: number
}

// ── 관련 뉴스 (지연 로딩 전용, KOSPI/부동산 단기 구간만) ────────────────────
export interface NewsArticle {
  title: string
  link: string
  published_at: string
}

export interface NewsResponse {
  articles: NewsArticle[]
}

export const PERIODS: PeriodDef[] = [
  { label: { ko: '전일', en: '1D'  }, value: '1d',    days: 1    },
  { label: { ko: '7일', en: '7D'   }, value: '7d',    days: 7    },
  { label: { ko: '30일', en: '30D' }, value: '30d',   days: 30   },
  { label: { ko: '90일', en: '90D' }, value: '90d',   days: 90   },
  { label: { ko: '1년', en: '1Y'   }, value: '365d',  days: 365  },
  { label: { ko: '5년', en: '5Y'   }, value: '1825d', days: 1825 },
]

export interface CapTierDef {
  label: { ko: string; en: string }
  value: CapTier
  /** 마켓별 간략 설명 (툴팁 등에 사용) */
  desc: { kospi: { ko: string; en: string }; nasdaq: { ko: string; en: string } }
}

export const CAP_TIERS: CapTierDef[] = [
  {
    label: { ko: '전체', en: 'All' },
    value: 'all',
    desc: {
      kospi:  { ko: '시총 제한 없음', en: 'No cap filter' },
      nasdaq: { ko: '시총 제한 없음', en: 'No cap filter' },
    },
  },
  {
    label: { ko: '소형', en: 'Small' },
    value: 'small',
    desc: {
      kospi:  { ko: '5,000억 미만', en: '< ₩500B' },
      nasdaq: { ko: '$2B 미만',     en: '< $2B'   },
    },
  },
  {
    label: { ko: '중형', en: 'Mid' },
    value: 'mid',
    desc: {
      kospi:  { ko: '5,000억 ~ 5조', en: '₩500B – ₩5T' },
      nasdaq: { ko: '$2B ~ $10B',    en: '$2B – $10B'   },
    },
  },
  {
    label: { ko: '대형', en: 'Large' },
    value: 'large',
    desc: {
      kospi:  { ko: '5조 이상', en: '≥ ₩5T' },
      nasdaq: { ko: '$10B 이상', en: '≥ $10B' },
    },
  },
]
