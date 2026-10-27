import { describe, expect, it } from 'vitest'
import { rankSearchResults } from './searchSort'

const item = (ticker: string, name: string | null) => ({ ticker, name })
const tickers = (xs: { ticker: string }[]) => xs.map((x) => x.ticker)

describe('rankSearchResults', () => {
  it('이름 완전 일치 > 이름 접두 > 티커 접두 > 나머지', () => {
    const items = [
      item('000810', '삼성화재'),
      item('028260', '삼성물산'),
      item('005930', '삼성전자'),
      item('207940', '삼성바이오로직스'),
      item('009150', '제일삼성'),
    ]
    expect(tickers(rankSearchResults(items, '삼성전자'))).toEqual(['005930', '000810', '028260', '207940', '009150'])
    expect(tickers(rankSearchResults(items, '삼성'))).toEqual(['000810', '028260', '005930', '207940', '009150'])
  })

  it('같은 그룹 안에서는 받은 순서 유지', () => {
    const items = [item('B1', '삼성B'), item('A1', '삼성A'), item('C1', '삼성C')]
    expect(tickers(rankSearchResults(items, '삼성'))).toEqual(['B1', 'A1', 'C1'])
  })

  it('티커 접두는 이름 일치보다 뒤', () => {
    const items = [item('AAPL', 'Apple Inc. Common Stock'), item('AAPB', 'GraniteShares 2x Long AAPL'), item('AA', 'Alcoa')]
    expect(tickers(rankSearchResults(items, 'aa'))).toEqual(['AAPL', 'AAPB', 'AA'])
    expect(tickers(rankSearchResults(items, 'apple'))).toEqual(['AAPL', 'AAPB', 'AA'])
  })

  it('표시 이름(Common Stock 꼬리 제거)으로도 완전 일치를 본다', () => {
    const items = [item('APLE', 'Apple Hospitality REIT'), item('AAPL', 'Apple Inc. Common Stock')]
    expect(tickers(rankSearchResults(items, 'apple inc.'))).toEqual(['AAPL', 'APLE'])
  })

  it('대소문자와 앞뒤 공백 무시, 이름이 없어도 동작', () => {
    const items = [item('X', null), item('MSFT', 'Microsoft Corporation - Common Stock')]
    expect(tickers(rankSearchResults(items, '  MICROSOFT CORPORATION '))).toEqual(['MSFT', 'X'])
  })

  it('빈 검색어면 그대로', () => {
    const items = [item('B', 'b'), item('A', 'a')]
    expect(rankSearchResults(items, ' ')).toBe(items)
  })
})
