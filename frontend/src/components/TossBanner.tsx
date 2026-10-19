import { useEffect, useRef, useState } from 'react'
import { TossAds } from '@apps-in-toss/web-framework'

// 광고 그룹 ID는 콘솔에서 발급받은 값을 VITE_TOSS_BANNER_AD_GROUP_ID로 주입한다.
// 값이 없으면 문서의 테스트 ID(리스트형 배너)를 쓴다 — 개발 중 실제 ID로 테스트하면 정책 위반이다.
// 출시 전에는 반드시 실제 ID를 넣어야 한다(검수는 테스트 광고가 아닌 실제 광고 노출을 요구).
const AD_GROUP_ID = import.meta.env.VITE_TOSS_BANNER_AD_GROUP_ID || 'ait-ad-test-banner-id'

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

/**
 * 앱인토스 인앱 광고(배너). 토스 광고 SDK만 쓰고 외부 광고 네트워크는 쓰지 않는다.
 * - 지원하지 않는 토스 앱 버전이거나 초기화/렌더링에 실패하거나 광고가 없으면 영역을 비운다.
 * - 한 화면에 한 개만, 스크롤되는 목록 아래에만 둔다(호출하는 쪽이 목록이 있을 때만 렌더링).
 * - 컨테이너는 SDK 가이드대로 width 100%, 고정형 높이 96px, 내부는 비워 둔다.
 */
export function TossBanner() {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    let cancelled = false
    let attached: { destroy: () => void } | undefined

    initTossAds().then((ready) => {
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
      attached?.destroy()
    }
  }, [])

  if (!visible) return null
  return <div ref={ref} style={{ width: '100%', height: 96 }} />
}
