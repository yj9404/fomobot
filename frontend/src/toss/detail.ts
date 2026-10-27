import { PERIODS } from '../types'
import type { Period } from '../types'
import type { StockDetail } from './api'

/** 상세 화면 계산 — 화면 컴포넌트와 분리해 테스트한다. */

export function fmtPct(n: number): string {
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

/** YYYY-MM-DD에서 달력 일수를 뺀다(UTC 기준이라 시간대와 무관). */
export function isoMinusDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() - days)
  return d.toISOString().slice(0, 10)
}

/** 기간 시작(as_of - N일) 이하의 마지막 시계열 지점부터 자른다 — 랭킹의 거래일 스냅과 같은 방향. */
export function sliceSeries(series: [string, number][], asOf: string, days: number): [string, number][] {
  const cutoff = isoMinusDays(asOf, days)
  let start = 0
  for (let i = 0; i < series.length; i++) {
    if (series[i]![0] <= cutoff) start = i
    else break
  }
  return series.slice(start)
}

/**
 * 이 기간의 계산 시작일이 종목 시계열의 첫날이고 그날이 기간 시작보다 늦으면,
 * 상장(또는 데이터 시작)이 기간 안에 있어 첫 거래일부터 계산한 값이다.
 */
export function listedWithin(d: StockDetail, period: Period): string | null {
  const ch = d.changes[period]
  const first = d.series[0]?.[0]
  const days = PERIODS.find((p) => p.value === period)!.days
  if (!ch || !first || !d.as_of) return null
  return ch.start_date === first && first > isoMinusDays(d.as_of, days) ? first : null
}
