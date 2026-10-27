import { CAP_TIERS, PERIODS } from '../types'
import type { CapTier, Market, OrderDir, Period } from '../types'

/**
 * 토스 미니앱 화면 경로. 순수 함수만 둔다(테스트 대상) — history 조작은 router.ts.
 *
 * 앱 안의 이동은 hash에 싣는다(#/stock?market=&ticker=). pathname을 쓰지 않는 이유:
 * 번들이 상대 경로(base './')로 서빙되고, 토스 정적 호스팅이 하위 경로를 index.html로
 * 돌려주는지 문서에 없어서 — hash는 호스팅 동작과 무관하다.
 *
 * 공유 딥링크(intoss://fomobot/stock?...)는 path + query로 같은 화면을 가리킨다.
 */

export type RankingsRoute = { name: 'rankings'; market: Market; period: Period; cap: CapTier; order: OrderDir }
export type Route =
  | RankingsRoute
  | { name: 'search'; q: string }
  | { name: 'stock'; market: Market; ticker: string }

export const APP_NAME = 'fomobot'

export const DEFAULT_RANKINGS: RankingsRoute = { name: 'rankings', market: 'kospi', period: '30d', cap: 'all', order: 'desc' }

const MARKETS: readonly Market[] = ['kospi', 'nasdaq']
const ORDERS: readonly OrderDir[] = ['desc', 'asc']
// NASDAQ 티커의 하이픈·점(클래스주 등)을 허용한다. shared/share.ts TICKER_RE와 같은 규칙.
const TICKER_RE = /^[A-Za-z0-9.-]{1,20}$/

function pick<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return allowed.includes(value as T) ? (value as T) : fallback
}

/** path('/', '/search', '/stock')와 쿼리로 화면을 정한다. 알 수 없는 경로나 잘못된 값은 순위 화면 기본값. */
export function parseRoute(path: string, params: URLSearchParams): Route {
  const name = path.replace(/^\/+|\/+$/g, '')
  if (name === 'search') return { name: 'search', q: (params.get('q') ?? '').slice(0, 100) }
  if (name === 'stock') {
    const market = params.get('market')
    const ticker = params.get('ticker')
    if (MARKETS.includes(market as Market) && ticker && TICKER_RE.test(ticker)) {
      return { name: 'stock', market: market as Market, ticker: ticker.toUpperCase() }
    }
    return DEFAULT_RANKINGS
  }
  return {
    name: 'rankings',
    market: pick(params.get('market'), MARKETS, DEFAULT_RANKINGS.market),
    period: pick(params.get('period'), PERIODS.map((p) => p.value as Period), DEFAULT_RANKINGS.period),
    cap: pick(params.get('cap'), CAP_TIERS.map((c) => c.value), DEFAULT_RANKINGS.cap),
    order: pick(params.get('order'), ORDERS, DEFAULT_RANKINGS.order),
  }
}

/** 화면 → path + query. hash와 공유 딥링크가 같은 형식을 쓴다. */
export function routeTarget(route: Route): { path: string; query: string } {
  switch (route.name) {
    case 'rankings':
      return { path: '/', query: new URLSearchParams({ market: route.market, period: route.period, cap: route.cap, order: route.order }).toString() }
    case 'search':
      return { path: '/search', query: route.q ? new URLSearchParams({ q: route.q }).toString() : '' }
    case 'stock':
      return { path: '/stock', query: new URLSearchParams({ market: route.market, ticker: route.ticker }).toString() }
  }
}

export function routeToHash(route: Route): string {
  const { path, query } = routeTarget(route)
  return `#${path}${query ? `?${query}` : ''}`
}

export function parseHash(hash: string): Route | null {
  if (!hash.startsWith('#/')) return null
  const body = hash.slice(1)
  const i = body.indexOf('?')
  return i < 0 ? parseRoute(body, new URLSearchParams()) : parseRoute(body.slice(0, i), new URLSearchParams(body.slice(i + 1)))
}

/** Share.createLink에 넘길 딥링크. 순위는 앱 루트(intoss://fomobot?...)로 연다. */
export function routeToDeepLink(route: Route): string {
  const { path, query } = routeTarget(route)
  const tail = path === '/' ? '' : path
  return `intoss://${APP_NAME}${tail}${query ? `?${query}` : ''}`
}

/**
 * 첫 진입 화면. Environment.initialURL(처음 진입한 스킴 URL, 이후 이동은 반영되지 않음)을 읽는다.
 *
 * - 스킴 URL이면 호스트(앱 이름)는 무시하고 path와 query만 본다.
 * - 출시 전 테스트 스킴은 쿼리를 queryParams=<URL 인코딩된 JSON>으로 넘기므로 그 형태도 받는다.
 * - 스킴이 아닌 값(devtools mock은 location.pathname)이면 현재 location을 쓴다.
 * - hash가 이미 있으면(웹뷰 새로고침) 진입 URL보다 그 화면을 우선한다.
 */
export function parseEntry(initialURL: string, location: { pathname: string; search: string; hash: string }): Route {
  const fromHash = parseHash(location.hash)
  if (fromHash) return fromHash
  const m = initialURL.match(/^[a-z][a-z0-9+.-]*:\/\/[^/?#]*([^?#]*)(?:\?([^#]*))?/i)
  if (!m) return parseRoute(location.pathname, new URLSearchParams(location.search))

  const params = new URLSearchParams(m[2] ?? '')
  const packed = params.get('queryParams')
  if (packed) {
    try {
      const obj: unknown = JSON.parse(packed)
      if (obj && typeof obj === 'object') {
        for (const [k, v] of Object.entries(obj)) {
          if (typeof v === 'string') params.set(k, v)
        }
      }
    } catch {
      // 형식이 깨진 queryParams는 무시하고 나머지 쿼리만 쓴다.
    }
  }
  return parseRoute(m[1] || '/', params)
}
