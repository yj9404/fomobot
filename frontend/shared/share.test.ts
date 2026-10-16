import { describe, expect, it } from 'vitest'
import {
  customPeriodLabel, daysBetween, fmtShareMoney, fmtSharePct, isFlatPct, parseShareParams, sharePath, shareText,
} from './share'

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

describe('shareText — 공유 시트·클립보드 문구', () => {
  it('상승', () => {
    expect(shareText('삼성전자', 121.5789, '1년', '2025-10-15', '2026-10-15'))
      .toBe('삼성전자, 1년 만에 121.6% 올랐어요.\n(2025-10-15 ~ 2026-10-15)')
  })

  it('하락은 부호 없이 "하락했어요"', () => {
    expect(shareText('SK하이닉스', -25.43, '7일', '2026-10-08', '2026-10-15'))
      .toBe('SK하이닉스, 7일 만에 25.4% 하락했어요.\n(2026-10-08 ~ 2026-10-15)')
  })

  it('반올림 0.0%는 변동 없음 문구', () => {
    expect(shareText('KT&G', -0.04, '30일', '2026-09-15', '2026-10-15'))
      .toBe('KT&G, 30일 동안 거의 변동이 없었어요.\n(2026-09-15 ~ 2026-10-15)')
    expect(shareText('KT&G', 0.05, '30일', '2026-09-15', '2026-10-15'))
      .toBe('KT&G, 30일 만에 0.1% 올랐어요.\n(2026-09-15 ~ 2026-10-15)')
  })

  it('기간 탭 라벨은 받은 그대로 쓴다(날짜로 역추정하지 않음)', () => {
    // 1년 탭이지만 휴장일 때문에 실제 구간은 366일
    expect(shareText('삼성전자', 10, '1년', '2025-10-14', '2026-10-15')).toContain(', 1년 만에 ')
  })

  it('직접 입력은 달력일 수', () => {
    expect(customPeriodLabel('2026-07-08', '2026-10-14')).toBe('98일')
    expect(shareText('삼성전자', 10, customPeriodLabel('2026-07-08', '2026-10-14'), '2026-07-08', '2026-10-14'))
      .toBe('삼성전자, 98일 만에 10.0% 올랐어요.\n(2026-07-08 ~ 2026-10-14)')
  })

  it('천 단위 콤마', () => {
    expect(shareText('Moonshot Therapeutics Inc.', 2441.67, '5년', '2021-10-14', '2026-10-14'))
      .toBe('Moonshot Therapeutics Inc., 5년 만에 2,441.7% 올랐어요.\n(2021-10-14 ~ 2026-10-14)')
  })

  it('NASDAQ 영문명', () => {
    expect(shareText('Apple Inc. - Common Stock', 37.1621, '1년', '2025-10-15', '2026-10-15'))
      .toBe('Apple Inc. - Common Stock, 1년 만에 37.2% 올랐어요.\n(2025-10-15 ~ 2026-10-15)')
  })
})
