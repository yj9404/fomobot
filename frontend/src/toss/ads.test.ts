import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// SDK 목: 저장소는 메모리 Map, 로드는 바로 loaded, 노출은 콜백을 잡아 두고 테스트가 이벤트를 보낸다.
const store = new Map<string, string>()
type ShowArgs = { options: { adGroupId: string }; onEvent: (e: { type: string; data?: unknown }) => void; onError: (e: Error) => void }
const shows: ShowArgs[] = []
const sdk = vi.hoisted(() => ({ loadFails: false }))

vi.mock('@apps-in-toss/web-framework', () => {
  const supported = () => true
  return {
    Storage: {
      getItem: async (k: string) => store.get(k) ?? null,
      setItem: async (k: string, v: string) => { store.set(k, v) },
    },
    loadFullScreenAd: Object.assign(
      (args: { onEvent: (e: { type: 'loaded' }) => void; onError: (e: Error) => void }) => {
        setTimeout(() => (sdk.loadFails ? args.onError(new Error('no fill')) : args.onEvent({ type: 'loaded' })), 0)
        return () => {}
      },
      { isSupported: supported },
    ),
    showFullScreenAd: Object.assign(
      (args: ShowArgs) => {
        shows.push(args)
        return () => {}
      },
      { isSupported: supported },
    ),
  }
})

type Ads = typeof import('./ads')
let ads: Ads

async function flush() {
  await vi.advanceTimersByTimeAsync(0)
  await vi.advanceTimersByTimeAsync(0)
}

/** 상세로 한 번 들어간다(목록 화면 preload → 탭). proceed가 불렸는지 돌려준다. */
async function enterDetail(): Promise<{ proceeded: () => boolean }> {
  ads.preloadDetailInterstitial()
  await flush()
  let proceeded = false
  ads.withDetailInterstitial(() => { proceeded = true })
  await flush()
  return { proceeded: () => proceeded }
}

function emit(type: string) {
  shows[shows.length - 1]!.onEvent({ type, ...(type === 'userEarnedReward' ? { data: { unitType: 'pass', unitAmount: 1 } } : {}) })
}

beforeEach(async () => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-27T00:00:00Z'))
  vi.spyOn(console, 'error').mockImplementation(() => {})
  store.clear()
  shows.length = 0
  sdk.loadFails = false
  vi.resetModules()
  ads = await import('./ads')
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('상세 전면광고', () => {
  it('4번째 진입에만 광고를 띄우고, 닫힌 뒤에 진행한다', async () => {
    for (let i = 0; i < 3; i++) expect((await enterDetail()).proceeded()).toBe(true)
    expect(shows).toHaveLength(0)

    const fourth = await enterDetail()
    expect(shows).toHaveLength(1)
    expect(fourth.proceeded()).toBe(false)
    emit('requested'); emit('show'); emit('impression')
    await flush()
    expect(fourth.proceeded()).toBe(false)
    emit('dismissed')
    await flush()
    expect(fourth.proceeded()).toBe(true)
  })

  it('쿨다운 중이면 건너뛰고 횟수는 그대로 이어간다', async () => {
    for (let i = 0; i < 3; i++) await enterDetail()
    await enterDetail()
    emit('show'); emit('dismissed')
    await flush()

    vi.advanceTimersByTime(30_000) // 90초 안
    for (let i = 0; i < 3; i++) await enterDetail()
    const eighth = await enterDetail()
    expect(eighth.proceeded()).toBe(true)
    expect(shows).toHaveLength(1)

    vi.advanceTimersByTime(ads.INTERSTITIAL_COOLDOWN_MS)
    for (let i = 0; i < 3; i++) await enterDetail()
    await enterDetail() // 12번째
    expect(shows).toHaveLength(2)
  })

  it('노출 실패·로드 실패면 막지 않고 진행한다', async () => {
    for (let i = 0; i < 3; i++) await enterDetail()
    const fourth = await enterDetail()
    shows[0]!.onError(new Error('boom'))
    await flush()
    expect(fourth.proceeded()).toBe(true)

    sdk.loadFails = true
    for (let i = 0; i < 3; i++) await enterDetail()
    expect((await enterDetail()).proceeded()).toBe(true)
    expect(shows).toHaveLength(1)
  })

  it('광고가 뜨지 않거나 dismissed가 오지 않아도 안전장치 시간 뒤 진행한다', async () => {
    for (let i = 0; i < 3; i++) await enterDetail()
    const fourth = await enterDetail()
    await vi.advanceTimersByTimeAsync(5_000)
    expect(fourth.proceeded()).toBe(true)
  })

  it('광고가 떠 있는 동안 들어온 탭은 무시한다', async () => {
    for (let i = 0; i < 3; i++) await enterDetail()
    await enterDetail()
    let second = false
    ads.withDetailInterstitial(() => { second = true })
    emit('show'); emit('dismissed')
    await flush()
    expect(second).toBe(false)
    expect(store.get('ads.detailEntryCount')).toBe('4')
  })

  it('진입 횟수는 앱을 다시 켜도 이어진다', async () => {
    for (let i = 0; i < 3; i++) await enterDetail()
    vi.resetModules()
    ads = await import('./ads')
    await enterDetail()
    expect(shows).toHaveLength(1)
  })
})

describe('광고 제거 이용권', () => {
  async function watchReward(events: string[]): Promise<number | null> {
    const loaded = ads.preloadAdFreeReward()
    await flush()
    expect(await loaded).toBe(true)
    const result = ads.showAdFreeReward()
    await flush()
    for (const e of events) emit(e)
    return result
  }

  it('보상 이벤트를 받으면 24시간 동안 전면광고를 건너뛴다', async () => {
    const until = await watchReward(['show', 'userEarnedReward', 'dismissed'])
    expect(until).toBe(Date.now() + ads.AD_FREE_MS)
    expect(store.get('ads.adFreeUntil')).toBe(String(until))

    for (let i = 0; i < 4; i++) expect((await enterDetail()).proceeded()).toBe(true)
    expect(shows).toHaveLength(1) // 보상형 1회뿐

    vi.advanceTimersByTime(ads.AD_FREE_MS)
    expect(await ads.getAdFreeUntil()).toBeNull()
    for (let i = 0; i < 4; i++) await enterDetail()
    expect(shows).toHaveLength(2)
  })

  it('끝까지 보지 않고 닫으면 이용권을 주지 않는다', async () => {
    expect(await watchReward(['show', 'dismissed'])).toBeNull()
    expect(store.has('ads.adFreeUntil')).toBe(false)
  })
})
