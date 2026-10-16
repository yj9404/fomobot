import { describe, expect, it } from 'vitest'
import { daysBetween, fmtShareMoney, fmtSharePct, isFlatPct, parseShareParams, sharePath } from './share'

const q = (s: string) => new URLSearchParams(s)

describe('parseShareParams', () => {
  it('정상 파라미터', () => {
    expect(parseShareParams('kospi', '005930', q('from=2025-10-15&to=2026-10-15')))
      .toEqual({ market: 'kospi', ticker: '005930', from: '2025-10-15', to: '2026-10-15' })
  })

  it('하이픈·점이 든 NASDAQ 티커 허용', () => {
    expect(parseShareParams('nasdaq', 'ABC-W', q('from=2025-10-15&to=2026-10-15'))).not.toBeNull()
    expect(parseShareParams('nasdaq', 'BRK.B', q('from=2025-10-15&to=2026-10-15'))).not.toBeNull()
  })

  it.each([
    ['kosdaq', '005930', 'from=2025-10-15&to=2026-10-15'],   // market 화이트리스트
    ['kospi', '00/5930', 'from=2025-10-15&to=2026-10-15'],   // 티커 문자 집합
    ['kospi', '005_930', 'from=2025-10-15&to=2026-10-15'],
    ['kospi', 'A'.repeat(21), 'from=2025-10-15&to=2026-10-15'],
    ['kospi', '005930', 'from=20251015&to=2026-10-15'],      // 날짜 형식
    ['kospi', '005930', 'to=2026-10-15'],                     // 누락
  ])('거부: %s/%s?%s', (market, ticker, search) => {
    expect(parseShareParams(market, ticker, q(search))).toBeNull()
  })

  it('수치 파라미터는 경로에 실리지 않는다', () => {
    const p = parseShareParams('kospi', '005930', q('from=2025-10-15&to=2026-10-15&ret=99999'))!
    expect(sharePath(p)).toBe('/s/kospi/005930?from=2025-10-15&to=2026-10-15')
  })
})

describe('fmtSharePct — backend og_card.fmt_pct와 같은 결과', () => {
  it.each([
    [50, '+50.0%'],
    [-5.04, '-5.0%'],
    [1234.56, '+1,234.6%'],
    [12.25, '+12.3%'],
    [-12.25, '-12.3%'],
    [0.04, '0.0%'],
    [-0.04, '0.0%'],
    [0.05, '+0.1%'],
  ])('%s → %s', (v, out) => {
    expect(fmtSharePct(v)).toBe(out)
  })

  it('반올림 0은 flat', () => {
    expect(isFlatPct(-0.04)).toBe(true)
    expect(isFlatPct(0.05)).toBe(false)
  })
})

describe('fmtShareMoney', () => {
  it('통화별 표기', () => {
    expect(fmtShareMoney(1_000_000, 'KRW')).toBe('₩1,000,000')
    expect(fmtShareMoney(1_614_754, 'KRW')).toBe('₩1,614,754')
    expect(fmtShareMoney(9_500, 'USD')).toBe('$9,500')
  })
})

describe('daysBetween', () => {
  it('캘린더 일수', () => {
    expect(daysBetween('2025-10-15', '2026-10-15')).toBe(365)
    expect(daysBetween('2026-10-01', '2026-10-15')).toBe(14)
  })
})
