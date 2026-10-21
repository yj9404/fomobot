import type { Market } from './types'

/**
 * 주가 표시. KOSPI는 원(정수, 4,040원), NASDAQ은 달러(소수 2자리, $1,234.56).
 * 백엔드 float 잡음(423.4800109863281)은 2자리 반올림으로 정리된다. 값이 없으면 "—".
 */
export function fmtPrice(value: number | null | undefined, market: Market): string {
  if (value == null) return '—'
  return market === 'kospi'
    ? `${Math.round(value).toLocaleString('ko-KR')}원`
    : `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
