import { describe, expect, it } from 'vitest'
import { DEFAULT_RANKINGS, parseEntry, parseHash, routeToDeepLink, routeToHash, type Route } from './routes'

const loc = (pathname = '/', search = '', hash = '') => ({ pathname, search, hash })

describe('hash 왕복', () => {
  const routes: Route[] = [
    { name: 'rankings', market: 'nasdaq', period: '365d', cap: 'large', order: 'asc' },
    { name: 'search', q: '삼성 전자' },
    { name: 'search', q: '' },
    { name: 'stock', market: 'nasdaq', ticker: 'BRK.B', chart: '90d' },
  ]
  it.each(routes)('%o', (route) => {
    expect(parseHash(routeToHash(route))).toEqual(route)
  })

  it('hash가 경로 형식이 아니면 null', () => {
    expect(parseHash('')).toBeNull()
    expect(parseHash('#top')).toBeNull()
  })
})

describe('잘못된 값', () => {
  it('순위 조건이 잘못되면 각 값만 기본값으로', () => {
    expect(parseHash('#/?market=kosdaq&period=2d&cap=large&order=up')).toEqual({ ...DEFAULT_RANKINGS, cap: 'large' })
  })

  it('상세의 시장·티커가 잘못되면 순위 화면', () => {
    expect(parseHash('#/stock?market=kosdaq&ticker=005930')).toEqual(DEFAULT_RANKINGS)
    expect(parseHash('#/stock?market=kospi&ticker=<script>')).toEqual(DEFAULT_RANKINGS)
    expect(parseHash('#/stock?market=kospi')).toEqual(DEFAULT_RANKINGS)
  })

  it('티커는 대문자로', () => {
    expect(parseHash('#/stock?market=nasdaq&ticker=aapl')).toEqual({ name: 'stock', market: 'nasdaq', ticker: 'AAPL', chart: '365d' })
  })

  it('차트 구간이 없거나 잘못되면 1년(1일 구간은 차트 탭에 없다)', () => {
    for (const q of ['', '&chart=2d', '&chart=1d']) {
      expect(parseHash(`#/stock?market=kospi&ticker=005930${q}`)).toEqual({ name: 'stock', market: 'kospi', ticker: '005930', chart: '365d' })
    }
  })

  it('알 수 없는 경로는 순위 화면', () => {
    expect(parseHash('#/backtest?x=1')).toEqual(DEFAULT_RANKINGS)
  })
})

describe('공유 딥링크', () => {
  it('상세는 /stock 경로에 차트 구간까지', () => {
    expect(routeToDeepLink({ name: 'stock', market: 'kospi', ticker: '005930', chart: '30d' }))
      .toBe('intoss://fomobot/stock?market=kospi&ticker=005930&chart=30d')
  })

  it('차트 구간이 생기기 전에 공유된 링크는 1년으로 연다', () => {
    expect(parseEntry('intoss://fomobot/stock?market=kospi&ticker=005930', loc()))
      .toEqual({ name: 'stock', market: 'kospi', ticker: '005930', chart: '365d' })
  })

  it('순위는 앱 루트에 조건 쿼리', () => {
    expect(routeToDeepLink({ name: 'rankings', market: 'kospi', period: '30d', cap: 'all', order: 'desc' }))
      .toBe('intoss://fomobot?market=kospi&period=30d&cap=all&order=desc')
  })

  it('만든 딥링크로 진입하면 같은 화면이 복원된다', () => {
    const routes: Route[] = [
      { name: 'stock', market: 'nasdaq', ticker: 'AAPL', chart: '1825d' },
      { name: 'rankings', market: 'nasdaq', period: '7d', cap: 'mid', order: 'asc' },
    ]
    for (const r of routes) expect(parseEntry(routeToDeepLink(r), loc())).toEqual(r)
  })
})

describe('진입 URL(Environment.initialURL)', () => {
  it('앱 루트만 있으면 순위 기본값', () => {
    expect(parseEntry('intoss://fomobot', loc())).toEqual(DEFAULT_RANKINGS)
    expect(parseEntry('intoss://fomobot/', loc())).toEqual(DEFAULT_RANKINGS)
  })

  it('테스트 스킴의 queryParams JSON도 읽는다(호스트는 무시)', () => {
    const packed = encodeURIComponent(JSON.stringify({ market: 'kospi', ticker: '005930' }))
    expect(parseEntry(`scheme-test://appsintoss/stock?_deploymentId=abc&queryParams=${packed}`, loc()))
      .toEqual({ name: 'stock', market: 'kospi', ticker: '005930', chart: '365d' })
  })

  it('깨진 queryParams는 무시하고 나머지 쿼리를 쓴다', () => {
    expect(parseEntry('intoss://fomobot/stock?market=kospi&ticker=005930&queryParams=%7Bbad', loc()))
      .toEqual({ name: 'stock', market: 'kospi', ticker: '005930', chart: '365d' })
  })

  it('스킴이 아니면(devtools mock) 현재 location을 쓴다', () => {
    expect(parseEntry('/', loc('/stock', '?market=nasdaq&ticker=MSFT'))).toEqual({ name: 'stock', market: 'nasdaq', ticker: 'MSFT', chart: '365d' })
    expect(parseEntry('', loc('/index.html'))).toEqual(DEFAULT_RANKINGS)
  })

  it('hash가 있으면(새로고침) 진입 URL보다 우선', () => {
    expect(parseEntry('intoss://fomobot/stock?market=kospi&ticker=005930', loc('/', '', '#/search?q=abc')))
      .toEqual({ name: 'search', q: 'abc' })
  })
})
