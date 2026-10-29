import { Storage, loadFullScreenAd, showFullScreenAd } from '@apps-in-toss/web-framework'
import { AD_GROUP_IDS } from './adGroups'

/**
 * 전면형·보상형 광고(인앱 광고 2.0 ver2). 사전 로드, 노출, 쿨다운, 광고 제거 이용권 판정을 이 모듈에서만 한다.
 * 배너는 components/TossBanner.tsx가 따로 맡고 이용권과 무관하다.
 *
 * 원칙: 광고는 기능을 막지 않는다. 미지원 환경·ID 미입력·로드 전·로드/노출 실패·저장소 오류는
 * 모두 "광고 없음"으로 보고 원래 동작을 바로 진행한다.
 */

/** 상세 진입 누적 횟수가 이 수의 배수일 때 전면광고를 띄운다. */
export const DETAIL_AD_EVERY = 4
/** 전면광고 사이 최소 간격(앱 전체). 메모리에만 두므로 앱을 다시 켜면 초기화된다. */
export const INTERSTITIAL_COOLDOWN_MS = 90_000
/** 보상형 광고를 끝까지 보면 이 기간 동안 전면광고를 건너뛴다. */
export const AD_FREE_MS = 24 * 60 * 60 * 1000

// 저장소 응답이 늦어도 화면 이동이 멈추지 않게 이 시간이 지나면 값이 없는 것으로 본다.
const STORAGE_TIMEOUT_MS = 1_000
// 로드 이벤트가 끝내 오지 않을 때 다음 로드를 막지 않도록 끊는다. 문서상 AdMob 최대 네트워크 타임아웃이 60초.
const LOAD_TIMEOUT_MS = 60_000
// show 호출 뒤 광고가 뜨지 않으면(requested/show 미수신) 원래 동작으로 넘어간다.
const SHOW_START_TIMEOUT_MS = 5_000
// 광고가 뜬 뒤 dismissed가 오지 않는 경우(문서: Android 5.255.0) 화면이 멈추지 않게 하는 안전장치.
const DISMISS_FALLBACK_MS = 60_000

const KEY_DETAIL_COUNT = 'ads.detailEntryCount'
const KEY_AD_FREE_UNTIL = 'ads.adFreeUntil'

// ── 영구 저장(SDK Storage — 네이티브 저장소, 앱을 꺼도 유지) ─────────────────────

interface Persisted {
  detailCount: number
  adFreeUntil: number
}

function withTimeout<T>(p: Promise<T>, ms: number, fallback: T): Promise<T> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(fallback), ms)
    p.then(resolve, () => resolve(fallback)).finally(() => clearTimeout(timer))
  })
}

async function readNumber(key: string): Promise<number> {
  const raw = await withTimeout(Promise.resolve().then(() => Storage.getItem(key)), STORAGE_TIMEOUT_MS, null)
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : 0
}

function writeNumber(key: string, n: number): void {
  Promise.resolve()
    .then(() => Storage.setItem(key, String(n)))
    .catch((e: unknown) => console.error('[ads] 저장 실패', key, e))
}

// 저장소는 한 번만 읽고 이후에는 메모리 값을 쓴다(쓰기는 메모리와 저장소에 같이).
let persisted: Promise<Persisted> | null = null
function readPersisted(): Promise<Persisted> {
  persisted ??= Promise.all([readNumber(KEY_DETAIL_COUNT), readNumber(KEY_AD_FREE_UNTIL)])
    .then(([detailCount, adFreeUntil]) => ({ detailCount, adFreeUntil }))
  return persisted
}

const isAdFree = (s: Persisted) => s.adFreeUntil > Date.now()

// ── 로드·노출 ──────────────────────────────────────────────────────────────

function available(adGroupId: string): boolean {
  if (!adGroupId) return false
  try {
    return loadFullScreenAd.isSupported() && showFullScreenAd.isSupported()
  } catch {
    return false
  }
}

const loaded = new Set<string>()
const loading = new Map<string, Promise<boolean>>()
// 문서: 여러 광고 그룹을 동시에 로드하면 일부 Android 버전에서 이벤트가 오지 않는다 → 한 번에 하나씩 로드한다.
let loadChain: Promise<unknown> = Promise.resolve()

/** 그룹당 하나만 미리 로드한다. 이미 로드됐거나 로드 중이면 그 결과를 돌려준다. */
function preload(adGroupId: string): Promise<boolean> {
  if (loaded.has(adGroupId)) return Promise.resolve(true)
  if (!available(adGroupId)) return Promise.resolve(false)
  const pending = loading.get(adGroupId)
  if (pending) return pending
  const p = loadChain.then(() => loadOnce(adGroupId)).then((ok) => {
    loading.delete(adGroupId)
    if (ok) loaded.add(adGroupId)
    return ok
  })
  loadChain = p
  loading.set(adGroupId, p)
  return p
}

function loadOnce(adGroupId: string): Promise<boolean> {
  return new Promise((resolve) => {
    let settled = false
    let unregister: (() => void) | undefined
    const done = (ok: boolean) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      unregister?.()
      resolve(ok)
    }
    const timer = setTimeout(() => done(false), LOAD_TIMEOUT_MS)
    try {
      const off = loadFullScreenAd({
        options: { adGroupId },
        onEvent: (e) => { if (e.type === 'loaded') done(true) },
        onError: (e) => {
          console.error('[ads] 광고 로드 실패', adGroupId, e)
          done(false)
        },
      })
      if (settled) off()
      else unregister = off
    } catch (e) {
      console.error('[ads] 광고 로드 실패', adGroupId, e)
      done(false)
    }
  })
}

/**
 * 로드된 광고를 띄우고, 닫히면(dismissed) resolve한다. 실패하거나 안전장치 시간이 지나도 resolve한다.
 * 안전장치로 먼저 resolve해도 보상 이벤트는 dismissed까지 계속 받는다.
 */
function show(
  adGroupId: string,
  on: { show?: () => void; reward?: () => void; startTimeoutMs?: number } = {},
): Promise<void> {
  // 한 번 띄운 광고는 다시 쓸 수 없다(문서) — 다음 노출 전에 새로 로드해야 한다.
  loaded.delete(adGroupId)
  return new Promise((resolve) => {
    let settled = false
    let ended = false
    let unregister: (() => void) | undefined
    const settle = () => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve()
    }
    const end = () => {
      settle()
      if (ended) return
      ended = true
      unregister?.()
    }
    let timer = setTimeout(settle, on.startTimeoutMs ?? SHOW_START_TIMEOUT_MS)
    const extend = () => {
      if (settled) return
      clearTimeout(timer)
      timer = setTimeout(settle, DISMISS_FALLBACK_MS)
    }
    try {
      const off = showFullScreenAd({
        options: { adGroupId },
        onEvent: (e) => {
          switch (e.type) {
            case 'requested':
              extend()
              break
            case 'show':
              extend()
              on.show?.()
              break
            case 'userEarnedReward':
              on.reward?.()
              break
            case 'dismissed':
            case 'failedToShow':
              end()
              break
          }
        },
        onError: (e) => {
          console.error('[ads] 광고 노출 실패', adGroupId, e)
          end()
        },
      })
      if (ended) off()
      else unregister = off
    } catch (e) {
      console.error('[ads] 광고 노출 실패', adGroupId, e)
      end()
    }
  })
}

// 전면형·보상형을 통틀어 한 번에 하나만 띄운다. 판정 중·노출 중에 들어온 호출(연타)은 무시한다.
let busy = false
let lastInterstitialAt = -Infinity

// ── 상세 전면광고 ──────────────────────────────────────────────────────────

/** 다음 상세 진입이 전면광고 차례면 미리 로드한다. 상세로 가는 목록·검색 화면에서 부른다. */
export function preloadDetailInterstitial(): void {
  void readPersisted().then((s) => {
    if ((s.detailCount + 1) % DETAIL_AD_EVERY !== 0 || isAdFree(s)) return
    void preload(AD_GROUP_IDS.detailInterstitial)
  })
}

/**
 * 상세 화면으로 이동하기 전에 부른다. 진입 횟수를 세고, 차례면 전면광고가 닫힌 뒤 proceed를 부른다.
 * 차례가 아니거나 이용권·쿨다운·미로드·실패로 광고를 건너뛰면 바로 proceed한다(횟수는 되돌리지 않는다).
 */
export function withDetailInterstitial(proceed: () => void): void {
  if (busy) return
  busy = true
  runDetailEntry()
    .catch((e: unknown) => console.error('[ads] 전면광고 처리 실패', e))
    .finally(() => {
      busy = false
      proceed()
    })
}

async function runDetailEntry(): Promise<void> {
  const s = await readPersisted()
  s.detailCount += 1
  writeNumber(KEY_DETAIL_COUNT, s.detailCount)

  const id = AD_GROUP_IDS.detailInterstitial
  if (s.detailCount % DETAIL_AD_EVERY !== 0) return
  if (isAdFree(s) || Date.now() - lastInterstitialAt < INTERSTITIAL_COOLDOWN_MS || !loaded.has(id)) return
  await show(id, { show: () => { lastInterstitialAt = Date.now() } })
}

// ── 광고 제거 이용권(보상형) ────────────────────────────────────────────────

/** 이 환경에서 이용권 광고를 쓸 수 있는지(지원 버전 + 그룹 ID 입력). */
export function isAdFreeRewardAvailable(): boolean {
  return available(AD_GROUP_IDS.adFreeReward)
}

/** 이용권 만료 시각(ms). 없거나 지났으면 null. */
export async function getAdFreeUntil(): Promise<number | null> {
  const s = await readPersisted()
  return isAdFree(s) ? s.adFreeUntil : null
}

// 보상 이벤트가 show의 resolve(안전장치 포함)보다 늦게 올 수 있어 받는 즉시 구독자에게 알린다.
// 실기기에서 보상을 받고도 버튼이 화면을 다시 그릴 때까지 바뀌지 않은 적이 있다.
const adFreeListeners = new Set<(until: number) => void>()

/** 이용권이 새로 생기면 만료 시각으로 cb를 부른다. 해제 함수를 돌려준다. */
export function subscribeAdFree(cb: (until: number) => void): () => void {
  adFreeListeners.add(cb)
  return () => { adFreeListeners.delete(cb) }
}

/** 이용권 버튼이 보일 때 보상형 광고를 미리 로드한다. 로드되면 true. */
export function preloadAdFreeReward(): Promise<boolean> {
  return preload(AD_GROUP_IDS.adFreeReward)
}

/**
 * 보상형 광고를 띄운다. 보상 이벤트(끝까지 시청)를 받았을 때만 "지금 + 24시간"을 저장한다 — dismissed만으로는 주지 않는다.
 * 광고가 닫힌 뒤 이용권 만료 시각(없으면 null)을 돌려준다.
 */
export async function showAdFreeReward(): Promise<number | null> {
  const id = AD_GROUP_IDS.adFreeReward
  if (busy || !loaded.has(id)) return getAdFreeUntil()
  busy = true
  try {
    const s = await readPersisted()
    await show(id, {
      // 보상형은 닫힌 뒤 이어갈 동작이 없으니 "광고가 안 떴다" 판정을 짧게 두지 않는다 —
      // 시청 중에 끝난 것으로 보고 다음 광고를 로드하거나 버튼을 되살리면 안 된다.
      startTimeoutMs: DISMISS_FALLBACK_MS,
      reward: () => {
        const until = Date.now() + AD_FREE_MS
        s.adFreeUntil = until
        writeNumber(KEY_AD_FREE_UNTIL, until)
        adFreeListeners.forEach((cb) => cb(until))
      },
    })
  } finally {
    busy = false
  }
  return getAdFreeUntil()
}
