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

// 마지막 " - " 뒤가 보통주를 뜻하는 꼬리일 때만 매칭한다($ 고정 + 꼬리 안에 " - "가 없어 항상 마지막 구간).
// Preferred·Warrant·Unit·Right·Notes나 "Depositary Shares, each representing ... Preferred"는 매칭되지 않는다 —
// 우선주(NFEGP 등)는 꼬리를 지우면 보통주(NFE)와 이름이 같아져 구분이 사라지기 때문.
const COMMON_SHARE_SUFFIX = /\s+-\s+(?:Class [A-Z]\s+)?(?:Common Stock|(?:Common|Ordinary|American Depositary) Shares?)$/i

/**
 * 표시 전용 종목명. NASDAQ 상장 명칭의 보통주 꼬리("- Common Stock" 등)만 떼어 랭킹 목록 폭을 아낀다.
 * DB·API 값과 검색에는 쓰지 않는다. 매칭되지 않으면 원문 그대로 돌려준다.
 */
export function displayStockName(name: string): string {
  return name.replace(COMMON_SHARE_SUFFIX, '') || name
}
