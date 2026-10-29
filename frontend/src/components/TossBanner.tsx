import { useEffect, useRef, useState } from 'react'
import { TossAds } from '@apps-in-toss/web-framework'
import { AD_GROUP_IDS } from '../toss/adGroups'

// 광고 그룹 ID는 toss/adGroups.ts 한 곳에 둔다(dev 서버는 테스트 ID, 빌드는 실제 ID).
const AD_GROUP_ID = AD_GROUP_IDS.banner

// SDK 초기화는 앱 전체에서 한 번만 한다.
let initPromise: Promise<boolean> | null = null
function initTossAds(): Promise<boolean> {
  initPromise ??= new Promise<boolean>((resolve) => {
    if (!TossAds.initialize.isSupported()) return resolve(false)
    TossAds.initialize({
      callbacks: {
        onInitialized: () => resolve(true),
        onInitializationFailed: (error) => {
          console.error('[TossBanner] 광고 SDK 초기화 실패', error)
          resolve(false)
        },
      },
    })
  })
  return initPromise
}

// 화면에 들어오기 이만큼 전부터 광고를 요청해, 스크롤해 닿았을 때 이미 그려져 있게 한다.
const PRELOAD_MARGIN = '200px 0px'

// 배너가 화면 근처에 올 때까지 기다린다. 미지원 환경에서는 바로 진행한다.
function whenNearViewport(el: HTMLElement): { promise: Promise<void>; cancel: () => void } {
  if (typeof IntersectionObserver === 'undefined') return { promise: Promise.resolve(), cancel: () => {} }
  let observer: IntersectionObserver | undefined
  const promise = new Promise<void>((resolve) => {
    observer = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) {
        observer?.disconnect()
        resolve()
      }
    }, { rootMargin: PRELOAD_MARGIN })
    observer.observe(el)
  })
  return { promise, cancel: () => observer?.disconnect() }
}

/**
 * 앱인토스 인앱 광고(배너). 토스 광고 SDK만 쓰고 외부 광고 네트워크는 쓰지 않는다.
 * - 지원하지 않는 토스 앱 버전이거나 초기화/렌더링에 실패하거나 광고가 없으면 영역을 비운다.
 * - 한 화면에 한 개만, 스크롤되는 목록 아래에만 둔다(호출하는 쪽이 목록이 있을 때만 렌더링).
 * - 마운트 즉시가 아니라 화면 근처에 왔을 때 광고를 요청한다. 첫 화면 아래에 두는 배너라
 *   즉시 요청하면 스크롤하지 않는 사용자에게 받기만 하고 노출하지 못한 광고가 쌓인다(수신 > 노출 시도).
 * - 컨테이너는 SDK 가이드대로 width 100%, 고정형 높이 102px(WebView SDK 3.0.5+), 내부는 비워 둔다.
 */
export function TossBanner() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    if (!ref.current) return
    let cancelled = false
    let attached: { destroy: () => void } | undefined
    const near = whenNearViewport(ref.current)

    Promise.all([initTossAds(), near.promise]).then(([ready]) => {
      if (cancelled) return
      if (!ready || !ref.current || !TossAds.attachBanner.isSupported()) {
        setVisible(false)
        return
      }
      attached = TossAds.attachBanner(AD_GROUP_ID, ref.current, {
        theme: 'light', // 토스 미니앱은 라이트 모드만 지원
        variant: 'expanded',
        callbacks: {
          onNoFill: () => setVisible(false),
          onAdFailedToRender: (payload) => {
            console.error('[TossBanner] 광고 렌더링 실패', payload.error.message)
            setVisible(false)
          },
        },
      })
    })

    return () => {
      cancelled = true
      near.cancel()
      attached?.destroy()
    }
  }, [])

  if (!visible) return null
  // 심의필·문구 줄바꿈으로 실제 높이가 달라질 수 있어 고정 height 대신 minHeight를 쓴다.
  return <div ref={ref} style={{ width: '100%', minHeight: 102 }} />
}
