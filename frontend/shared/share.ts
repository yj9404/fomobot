/**
 * 공유 카드 — Worker(worker/index.ts)와 공유 랜딩(src/components/SharePage.tsx)이 함께 쓰는
 * 파라미터 검증과 숫자 표기.
 *
 * 표기 규칙은 backend og_card.py(fmt_pct, fmt_money)와 같아야 한다. 카드 이미지,
 * OG 메타, 랜딩 화면의 숫자가 한 글자라도 다르면 안 되기 때문이다.
 */

export type ShareMarket = 'kospi' | 'nasdaq'
export type ShareCurrency = 'KRW' | 'USD'

/** backend GET /api/share 응답 = Worker /og/{market}/{ticker}.json 본문 */
export interface ShareData {
  market: ShareMarket
  ticker: string
  name: string
  from: string
  to: string
  start_price: number
  end_price: number
  return_pct: number
  mdd_pct: number
  principal: number
  end_value: number
  currency: ShareCurrency
}

export interface ShareParams {
  market: ShareMarket
  ticker: string
  from: string
  to: string
}

const MARKETS: readonly string[] = ['kospi', 'nasdaq']
// NASDAQ 티커의 하이픈(클래스주·워런트 표기 등)을 허용한다.
export const TICKER_RE = /^[A-Za-z0-9.-]{1,20}$/
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

/**
 * 형식만 검증한다(존재·거래일 여부는 backend가 판단). 통과한 값만 R2 키와
 * backend 호출에 쓰이므로, 여기서 걸러진 값은 Railway까지 가지 않는다.
 */
export function parseShareParams(
  market: string, ticker: string, search: URLSearchParams,
): ShareParams | null {
  const from = search.get('from')
  const to = search.get('to')
  if (!MARKETS.includes(market) || !TICKER_RE.test(ticker)) return null
  if (!from || !to || !DATE_RE.test(from) || !DATE_RE.test(to)) return null
  return { market: market as ShareMarket, ticker, from, to }
}

/** 검증된 값만으로 다시 만든 쿼리 — 임의 파라미터(?ret=99999 등)는 어디에도 실리지 않는다. */
export function shareQuery(p: { from: string; to: string }): string {
  return `?from=${p.from}&to=${p.to}`
}

export function sharePath(p: ShareParams): string {
  return `/s/${p.market}/${p.ticker}${shareQuery(p)}`
}

function withCommas(intPart: string): string {
  return intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * 소수 첫째 자리 % 표기. toFixed(1)은 float의 실제 2진 값 기준으로 .x5를 0에서 먼 쪽으로
 * 올린다 — og_card.round1과 같은 규칙. 반올림 결과가 0.0이면 부호 없이 "0.0%".
 * MDD(항상 ≤ 0)에도 그대로 쓴다.
 */
export function fmtSharePct(v: number): string {
  if (isFlatPct(v)) return '0.0%'
  return `${v > 0 ? '+' : '-'}${fmtAbsPct(v)}`
}

/** 부호 없는 절댓값 표기("2,441.7%") — 반올림 규칙은 fmtSharePct와 같다. */
function fmtAbsPct(v: number): string {
  const [i, d] = Math.abs(v).toFixed(1).split('.')
  return `${withCommas(i!)}.${d}%`
}

/** 반올림 결과가 0.0%면 상승/하락 어느 쪽 색도 쓰지 않는다(og_card.is_flat). */
export function isFlatPct(v: number): boolean {
  return Math.abs(v).toFixed(1) === '0.0'
}

export function fmtShareMoney(v: number, currency: ShareCurrency): string {
  return `${currency === 'KRW' ? '₩' : '$'}${withCommas(String(v))}`
}

/** from~to 캘린더 일수. "오늘 기준으로 다시 보기" 딥링크의 days 값. */
export function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000)
}

/**
 * 기간 탭의 공유 문구용 표기. 화면 탭 라벨을 그대로 쓰되, 1d 탭("전일")은
 * "전일 만에"가 어색해 "하루"로 바꾼다. 화면의 탭 라벨 자체는 바꾸지 않는다.
 */
export function tabPeriodLabel(tab: { value: string; label: { ko: string } }): string {
  return tab.value === '1d' ? '하루' : tab.label.ko
}

/**
 * navigator.share에 넘길 데이터. 공유 대상이 쓰는 필드가 플랫폼마다 달라 분기한다(실측).
 *  - Android: text와 url을 이어 붙여 본문으로 넘긴다 → text+url이면 "문구 링크"로 정상.
 *  - Windows: 공유창 미리보기에는 title을 보여 주지만, 링크 복사·카카오톡 PC 등 실제
 *    대상에는 url만 넘긴다 → url 필드를 빼고 링크를 text 끝에 붙여 하나로 보낸다.
 *    (url이 없어도 카카오톡은 본문 속 링크로 미리보기 카드를 만든다)
 */
export function buildShareData(text: string, url: string, userAgent: string): WebShareData {
  if (/Windows/.test(userAgent)) return { text: `${text}\n${url}` }
  return { title: text.replace(/\n/g, ' '), text, url }
}

export type WebShareData = { title?: string; text: string; url?: string }

/** 직접 입력 기간의 공유 문구용 표기 — from~to 달력일 수. */
export function customPeriodLabel(from: string, to: string): string {
  return `${daysBetween(from, to)}일`
}

/**
 * 공유 시트·클립보드에 실리는 문구(URL 제외).
 *
 * periodLabel은 조회 당시 UI 상태에서 받는다 — 기간 탭이면 탭 라벨, 직접 입력이면
 * customPeriodLabel. from/to 날짜로 탭을 역추정하지 않는다(휴장일 때문에 365일 탭이
 * 363일·366일로 어긋난다).
 */
export function shareText(
  name: string, returnPct: number, periodLabel: string, from: string, to: string,
): string {
  const head = isFlatPct(returnPct)
    ? `${name}, ${periodLabel} 동안 거의 변동이 없었어요.`
    : `${name}, ${periodLabel} 만에 ${fmtAbsPct(returnPct)} ${returnPct > 0 ? '올랐어요' : '하락했어요'}.`
  return `${head}\n(${from} ~ ${to})`
}
