/**
 * FomoBot Worker — 공유 카드 경로만 처리한다.
 *
 * wrangler.jsonc의 assets.run_worker_first가 /s/*, /og/*만 이 Worker로 보내고,
 * 나머지 경로는 지금처럼 정적 자산이 직접 서빙된다(not_found_handling 그대로).
 *
 *   /og/{market}/{ticker}.png?from&to   카드 PNG
 *   /og/{market}/{ticker}.json?from&to  카드 수치 JSON (공유 랜딩이 읽는다)
 *   /s/{market}/{ticker}?from&to        공유 랜딩 — index.html에 OG 메타를 주입
 *
 * 캐시: R2(OG_BUCKET)가 영구 캐시다. 같은 URL이면 내용이 영원히 같아야 하므로
 * PNG와 JSON 모두 R2에 한 번 저장된 것을 원천으로 쓴다. /s/ 메타와 랜딩 화면이
 * 같은 JSON을 읽어야 카드 이미지와 페이지 숫자가 갈라지지 않는다.
 * R2 miss면 backend-stock(API_BASE)을 호출하고, 200 + 기대한 content-type일 때만 저장한다.
 *
 * 수치는 URL로 받지 않는다. URL에서 쓰는 값은 market, ticker, from, to뿐이고
 * 형식 검증을 통과한 값만 R2 키와 backend 호출에 쓴다.
 */

import {
  fmtShareMoney, fmtSharePct, parseShareParams, sharePath, shareQuery,
  type ShareData, type ShareParams,
} from '../shared/share'

interface Env {
  ASSETS: Fetcher
  OG_BUCKET: R2Bucket
  API_BASE: string
}

type Kind = 'png' | 'json'

/** 카드 디자인 버전. 디자인(backend og_card.py)이나 JSON 스키마를 바꾸면 올린다. */
const CACHE_VERSION = 'v1'
const API_TIMEOUT_MS = 8000

const IMMUTABLE = 'public, max-age=31536000, immutable'
const NO_STORE = 'no-store'
// 랜딩 HTML은 해시된 JS/CSS를 참조하므로 재배포 후 옛 HTML이 남지 않게 정적 자산과 같은 정책.
const HTML_CACHE = 'public, max-age=0, must-revalidate'

const CONTENT_TYPE: Record<Kind, string> = { png: 'image/png', json: 'application/json' }

function r2Key(p: ShareParams, kind: Kind): string {
  return `og/${CACHE_VERSION}/${p.market}/${p.ticker}/${p.from}_${p.to}.${kind}`
}

function apiUrl(env: Env, p: ShareParams, kind: Kind): string {
  const path = kind === 'png' ? `/api/og/${p.market}/${p.ticker}.png` : `/api/share/${p.market}/${p.ticker}`
  return `${env.API_BASE}${path}${shareQuery(p)}`
}

type Fetched =
  | { ok: true; body: ArrayBuffer; cache: 'HIT' | 'MISS' }
  | { ok: false; status: number; body: string }

async function fetchCached(env: Env, p: ShareParams, kind: Kind): Promise<Fetched> {
  const key = r2Key(p, kind)
  const hit = await env.OG_BUCKET.get(key)
  if (hit) return { ok: true, body: await hit.arrayBuffer(), cache: 'HIT' }

  let res: Response
  try {
    res = await fetch(apiUrl(env, p, kind), { signal: AbortSignal.timeout(API_TIMEOUT_MS) })
  } catch (e) {
    const timedOut = e instanceof Error && e.name === 'TimeoutError'
    return {
      ok: false,
      status: timedOut ? 504 : 502,
      body: JSON.stringify({ detail: timedOut ? 'upstream timeout' : 'upstream unavailable' }),
    }
  }
  const contentType = res.headers.get('content-type') ?? ''
  if (res.status !== 200 || !contentType.startsWith(CONTENT_TYPE[kind])) {
    // 오류 응답은 저장하지 않는다. 400/404는 그대로, 그 밖의 실패는 502로 정리.
    const status = res.status === 400 || res.status === 404 ? res.status : 502
    return { ok: false, status, body: await res.text() }
  }
  const body = await res.arrayBuffer()
  await env.OG_BUCKET.put(key, body, { httpMetadata: { contentType: CONTENT_TYPE[kind] } })
  return { ok: true, body, cache: 'MISS' }
}

/**
 * 같은 카드의 다른 형식(PNG↔JSON)을 미리 채운다. 둘이 서로 다른 시점에 처음 계산되면
 * 그 사이에 price_daily 정정이 끼어들 경우 이미지와 숫자가 갈라질 수 있어서,
 * 한쪽이 처음 만들어질 때 다른 쪽도 같이 만들어 그 간격을 최소화한다.
 */
async function warm(env: Env, p: ShareParams, kind: Kind): Promise<void> {
  if (await env.OG_BUCKET.head(r2Key(p, kind))) return
  await fetchCached(env, p, kind)
}

function redirectCanonical(url: URL, path: string, p: ShareParams): Response {
  return Response.redirect(`${url.origin}${path}${shareQuery(p)}`, 301)
}

async function handleOg(
  url: URL, env: Env, ctx: ExecutionContext, market: string, ticker: string, kind: Kind,
): Promise<Response> {
  const p = parseShareParams(market, ticker, url.searchParams)
  if (!p) {
    return new Response('invalid share card parameters', {
      status: 400,
      headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': NO_STORE },
    })
  }
  const upper = p.ticker.toUpperCase()
  if (upper !== p.ticker) {
    return redirectCanonical(url, `/og/${p.market}/${upper}.${kind}`, { ...p, ticker: upper })
  }

  const r = await fetchCached(env, p, kind)
  if (!r.ok) {
    return new Response(r.body, {
      status: r.status,
      headers: {
        'Content-Type': kind === 'json' ? 'application/json' : 'text/plain; charset=utf-8',
        'Cache-Control': NO_STORE,
      },
    })
  }
  if (r.cache === 'MISS') ctx.waitUntil(warm(env, p, kind === 'png' ? 'json' : 'png'))
  return new Response(r.body, {
    headers: {
      'Content-Type': CONTENT_TYPE[kind],
      'Cache-Control': IMMUTABLE,
      'X-OG-Cache': r.cache,
    },
  })
}

// ── 메타 주입 — 숫자 표기는 shared/share.ts(= backend og_card.py와 같은 규칙) ──

function setContent(value: string): HTMLRewriterElementContentHandlers {
  // setAttribute는 값을 이스케이프한다 — 종목명 등 데이터는 이 경로로만 넣는다.
  return { element(el) { el.setAttribute('content', value) } }
}

const removeCanonical: HTMLRewriterElementContentHandlers = { element(el) { el.remove() } }
const appendNoindex: HTMLRewriterElementContentHandlers = {
  element(el) {
    // 데이터가 섞이지 않는 고정 마크업이라 html 모드로 넣는다.
    el.append('<meta name="robots" content="noindex" />', { html: true })
  },
}

function htmlResponse(body: ReadableStream | null, status: number): Response {
  return new Response(body, {
    status,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': HTML_CACHE,
      'X-Robots-Tag': 'noindex',
    },
  })
}

/** 카드를 만들 수 없을 때 — 기본 메타 유지 + noindex. 프론트가 에러 화면을 그린다. */
function fallbackPage(index: Response, status: number): Response {
  const rewritten = new HTMLRewriter()
    .on('link[rel="canonical"]', removeCanonical)
    .on('head', appendNoindex)
    .transform(index)
  return htmlResponse(rewritten.body, status)
}

function sharePage(index: Response, origin: string, p: ShareParams, d: ShareData): Response {
  const pageUrl = `${origin}${sharePath(p)}`
  const imageUrl = `${origin}/og/${p.market}/${p.ticker}.png${shareQuery(p)}`
  const title = `${d.name} ${fmtSharePct(d.return_pct)} (${p.from}~${p.to}) — FomoBot`
  const description =
    `${fmtShareMoney(d.principal, d.currency)} → ${fmtShareMoney(d.end_value, d.currency)}. ` +
    `기간 중 최대 하락 ${fmtSharePct(d.mdd_pct)}. ${p.to} 종가 기준.`

  const rewritten = new HTMLRewriter()
    .on('title', { element(el) { el.setInnerContent(title) } })
    .on('meta[name="description"]', setContent(description))
    .on('meta[property="og:type"]', setContent('website'))
    .on('meta[property="og:title"]', setContent(title))
    .on('meta[property="og:description"]', setContent(description))
    .on('meta[property="og:url"]', setContent(pageUrl))
    .on('meta[property="og:image"]', setContent(imageUrl))
    .on('meta[property="og:image:width"]', setContent('1200'))
    .on('meta[property="og:image:height"]', setContent('630'))
    .on('meta[name="twitter:card"]', setContent('summary_large_image'))
    .on('meta[name="twitter:title"]', setContent(title))
    .on('meta[name="twitter:description"]', setContent(description))
    .on('meta[name="twitter:image"]', setContent(imageUrl))
    .on('link[rel="canonical"]', removeCanonical)
    .on('head', appendNoindex)
    .transform(index)
  return htmlResponse(rewritten.body, 200)
}

async function handleShare(
  url: URL, env: Env, ctx: ExecutionContext, market: string, ticker: string,
): Promise<Response> {
  const p = parseShareParams(market, ticker, url.searchParams)
  if (p) {
    const upper = p.ticker.toUpperCase()
    if (upper !== p.ticker) return redirectCanonical(url, `/s/${p.market}/${upper}`, { ...p, ticker: upper })
  }

  // /index.html을 직접 요청하면 html_handling이 /로 307 리다이렉트하므로 /를 요청한다.
  const indexPromise = env.ASSETS.fetch(new Request(new URL('/', url)))
  if (!p) return fallbackPage(await indexPromise, 404)

  const [index, r] = await Promise.all([indexPromise, fetchCached(env, p, 'json')])
  if (!r.ok) {
    // 4xx = 존재하지 않는 카드(404). 5xx/타임아웃은 일시 장애라 크롤러가 영구 부재로
    // 기록하지 않도록 503으로 구분한다.
    return fallbackPage(index, r.status >= 500 ? 503 : 404)
  }
  if (r.cache === 'MISS') ctx.waitUntil(warm(env, p, 'png'))
  const data = JSON.parse(new TextDecoder().decode(r.body)) as ShareData
  return sharePage(index, url.origin, p, data)
}

const OG_PATH = /^\/og\/([^/]+)\/([^/]+)\.(png|json)$/
const SHARE_PATH = /^\/s\/([^/]+)\/([^/]+)\/?$/

export default {
  async fetch(request, env, ctx): Promise<Response> {
    const url = new URL(request.url)
    const isRead = request.method === 'GET' || request.method === 'HEAD'

    const og = url.pathname.match(OG_PATH)
    if (og && isRead) return handleOg(url, env, ctx, og[1]!, og[2]!, og[3] as Kind)

    const share = url.pathname.match(SHARE_PATH)
    if (share && isRead) return handleShare(url, env, ctx, share[1]!, share[2]!)

    // run_worker_first 패턴에 걸렸지만 형식이 다른 경로(/og/foo 등) — 정적 자산 처리에
    // 그대로 넘겨 기존과 같은 404 페이지가 나가게 한다.
    return env.ASSETS.fetch(request)
  },
} satisfies ExportedHandler<Env>
