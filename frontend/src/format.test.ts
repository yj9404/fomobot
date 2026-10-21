import { describe, expect, it } from 'vitest'
import { displayStockName, fmtPrice } from './format'

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

describe('displayStockName', () => {
  it('보통주 꼬리는 대소문자 무관하게 뗀다', () => {
    expect(displayStockName('Swarmer, Inc - common stock')).toBe('Swarmer, Inc')
    expect(displayStockName('Cue Biopharma, Inc. - Common Stock')).toBe('Cue Biopharma, Inc.')
    expect(displayStockName('Cipher Digital Inc. - Common Stock')).toBe('Cipher Digital Inc.')
    expect(displayStockName('Alphabet Inc. - Class A Common Stock')).toBe('Alphabet Inc.')
    expect(displayStockName('Bausch Health Companies Inc. - Common Shares')).toBe('Bausch Health Companies Inc.')
    expect(displayStockName('Arm Holdings plc - Ordinary Shares')).toBe('Arm Holdings plc')
    expect(displayStockName('XP Inc. - Class A Ordinary Shares')).toBe('XP Inc.')
    expect(displayStockName('Alibaba Group Holding Limited - American Depositary Shares')).toBe('Alibaba Group Holding Limited')
  })

  it('우선주·워런트·유닛·라이트·채권은 원문 유지(보통주와 구분해야 함)', () => {
    const keep = [
      'New Fortress Energy Inc. - 9.25% Fixed-to-Floating Rate Series B Cumulative Redeemable Perpetual Preferred Stock',
      'Some Bank Corp - Depositary Shares, each representing a 1/40th interest in a share of Series A Preferred Stock',
      'Some Bank Corp - Depositary Shares',
      'Abony Acquisition Corp. I - Warrant',
      'Artius II Acquisition Inc. - Rights',
      'Abony Acquisition Corp. I - Units',
      'Some Corp - 6.50% Senior Notes due 2029',
    ]
    for (const name of keep) expect(displayStockName(name)).toBe(name)
  })

  it('하이픈 없는 이름, 이름 중간 하이픈은 원문 유지', () => {
    expect(displayStockName('Apple Inc.')).toBe('Apple Inc.')
    expect(displayStockName('Coca-Cola Consolidated, Inc.')).toBe('Coca-Cola Consolidated, Inc.')
    expect(displayStockName('Common Stock Holdings Inc.')).toBe('Common Stock Holdings Inc.')
  })

  it('마지막 " - " 구간만 본다', () => {
    expect(displayStockName('Foo - Bar Inc. - Common Stock')).toBe('Foo - Bar Inc.')
    expect(displayStockName('Foo - Common Stock Warrant')).toBe('Foo - Common Stock Warrant')
  })

  it('KOSPI 종목명에는 영향 없음', () => {
    for (const name of ['삼성전자', '미래에셋증권2우B', 'SK하이닉스', 'LG에너지솔루션', 'KODEX 200']) {
      expect(displayStockName(name)).toBe(name)
    }
  })

  it('꼬리만 있는 이름은 빈 문자열 대신 원문 유지', () => {
    expect(displayStockName(' - Common Stock')).toBe(' - Common Stock')
  })
})
