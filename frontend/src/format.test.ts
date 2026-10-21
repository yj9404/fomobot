import { describe, expect, it } from 'vitest'
import { fmtPrice } from './format'

describe('fmtPrice', () => {
  it('KOSPI는 콤마 + 원, 소수점 없음', () => {
    expect(fmtPrice(4040, 'kospi')).toBe('4,040원')
    expect(fmtPrice(1234567.6, 'kospi')).toBe('1,234,568원')
  })

  it('NASDAQ은 $ 접두, 콤마, 소수 2자리', () => {
    expect(fmtPrice(1234.56, 'nasdaq')).toBe('$1,234.56')
    expect(fmtPrice(5, 'nasdaq')).toBe('$5.00')
  })

  it('float 잡음은 2자리로 정리', () => {
    expect(fmtPrice(423.4800109863281, 'nasdaq')).toBe('$423.48')
  })

  it('값이 없으면 대시', () => {
    expect(fmtPrice(null, 'kospi')).toBe('—')
    expect(fmtPrice(undefined, 'nasdaq')).toBe('—')
  })
})
