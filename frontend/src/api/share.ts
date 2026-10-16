import { shareQuery, type ShareData, type ShareParams } from '../../shared/share'

export type ShareCardResult =
  | { status: 'ok'; data: ShareData }
  | { status: 'invalid' }       // 존재하지 않는 카드 (400/404)
  | { status: 'unavailable' }   // 일시 장애 (5xx, 네트워크)

/**
 * 공유 카드 수치. Railway를 직접 부르지 않고 Worker 경로(R2 캐시)를 읽는다 —
 * OG 메타와 카드 이미지가 같은 JSON을 원천으로 쓰므로 랜딩 화면 숫자도 이걸 써야 한다.
 */
export async function fetchShareCard(p: ShareParams, signal?: AbortSignal): Promise<ShareCardResult> {
  let res: Response
  try {
    res = await fetch(`/og/${p.market}/${p.ticker}.json${shareQuery(p)}`, { signal })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    return { status: 'unavailable' }
  }
  if (res.ok) return { status: 'ok', data: (await res.json()) as ShareData }
  return res.status >= 500 ? { status: 'unavailable' } : { status: 'invalid' }
}
