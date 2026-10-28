import { describe, expect, it } from 'vitest'
import { daysSince, fmtPct, isoMinusDays, listedWithin, sliceSeries, todayKst } from './detail'
import type { StockDetail } from './api'

describe('isoMinusDays', () => {
  it('달력 일수를 뺀다(윤년·월말 포함)', () => {
    expect(isoMinusDays('2026-10-27', 30)).toBe('2026-09-27')
    expect(isoMinusDays('2024-03-01', 1)).toBe('2024-02-29')
    expect(isoMinusDays('2026-10-27', 1825)).toBe('2021-10-28')
  })
})

describe('sliceSeries', () => {
  const s: [string, number][] = [['2026-09-20', 1], ['2026-09-25', 2], ['2026-09-30', 3], ['2026-10-27', 4]]

  it('기간 시작 이하의 마지막 지점부터 자른다', () => {
    // 30일 전 = 09-27 → 그 이하 마지막 지점 09-25
    expect(sliceSeries(s, '2026-10-27', 30)).toEqual(s.slice(1))
  })

  it('시계열이 기간보다 짧으면 전부', () => {
    expect(sliceSeries(s, '2026-10-27', 1825)).toEqual(s)
  })
})

describe('listedWithin', () => {
  const base: StockDetail = {
    market: 'kospi', ticker: '111111', name: '신규', is_active: true, status: 'ok',
    as_of: '2026-10-27', close: 1, close_date: '2026-10-27',
    changes: {
      '1d': { change_pct: 1, start_date: '2026-10-26', end_date: '2026-10-27' },
      '7d': null, '30d': null, '90d': null,
      '365d': { change_pct: 1, start_date: '2026-05-04', end_date: '2026-10-27' },
      '1825d': { change_pct: 1, start_date: '2026-05-04', end_date: '2026-10-27' },
    },
    series: [['2026-05-04', 1], ['2026-10-26', 1], ['2026-10-27', 1]],
  }

  it('상장이 기간 안이면 첫 거래일을 돌려준다', () => {
    expect(listedWithin(base, '365d')).toBe('2026-05-04')
    expect(listedWithin(base, '1825d')).toBe('2026-05-04')
  })

  it('기간 시작에 이미 거래 중이었으면 null', () => {
    expect(listedWithin(base, '1d')).toBeNull()
  })

  it('등락률이 없으면 null', () => {
    expect(listedWithin(base, '30d')).toBeNull()
  })
})

describe('fmtPct', () => {
  it('부호와 소수 첫째 자리', () => {
    expect(fmtPct(5)).toBe('+5.0%')
    expect(fmtPct(-1.16)).toBe('-1.2%')
  })
})

describe('todayKst', () => {
  it('UTC 15시부터 한국 날짜가 넘어간다', () => {
    expect(todayKst(Date.parse('2026-10-27T14:59:00Z'))).toBe('2026-10-27')
    expect(todayKst(Date.parse('2026-10-27T15:00:00Z'))).toBe('2026-10-28')
  })
})

describe('daysSince', () => {
  it('달력 일수를 센다(월말 포함)', () => {
    expect(daysSince('2026-10-28', '2026-10-28')).toBe(0)
    expect(daysSince('2026-10-27', '2026-10-28')).toBe(1)
    expect(daysSince('2026-09-30', '2026-10-02')).toBe(2)
  })

  it('미래 날짜는 0', () => {
    expect(daysSince('2026-10-29', '2026-10-28')).toBe(0)
  })
})
