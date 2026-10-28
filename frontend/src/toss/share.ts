import { Share } from '@apps-in-toss/web-framework'
import { routeToDeepLink, type Route } from './routes'

/**
 * 토스 공유 — 토스 딥링크(intoss://)만 공유하고 웹 링크는 쓰지 않는다.
 *
 * 미리보기 이미지는 backend /api/og/toss/*(1200×600)를 https 절대 주소로 넘긴다.
 * 그 응답은 immutable 1년 캐시라, 카드 디자인이나 렌더링을 고치면 CARD_VERSION을 올려
 * 새 URL을 만든다(서버는 v를 읽지 않는다 — 캐시 키 역할만).
 */
export const CARD_VERSION = 2

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

/** ogImageUrl은 https 절대 경로여야 한다. dev 서버(상대 경로 프록시)에서는 이미지 없이 공유한다. */
export function ogImageUrl(route: Route, asOf: string): string | undefined {
  if (!API_BASE.startsWith('https://')) return undefined
  let path: string
  let query: URLSearchParams
  if (route.name === 'stock') {
    path = `/api/og/toss/stock/${route.market}/${encodeURIComponent(route.ticker)}.png`
    query = new URLSearchParams({ chart: route.chart, date: asOf })
  } else if (route.name === 'rankings') {
    path = `/api/og/toss/rankings/${route.market}.png`
    query = new URLSearchParams({ period: route.period, cap: route.cap, order: route.order, date: asOf })
  } else {
    return undefined
  }
  query.set('v', String(CARD_VERSION))
  return `${API_BASE}${path}?${query.toString()}`
}

/** 링크를 만들고 공유 시트를 연다. 실패하면 throw — 호출부가 안내 문구를 띄운다. */
export async function shareRoute(route: Route, asOf: string, message: string): Promise<void> {
  const link = await Share.createLink({ path: routeToDeepLink(route), ogImageUrl: ogImageUrl(route, asOf) })
  await Share.sendMessage({ message: `${message}\n${link}` })
}
