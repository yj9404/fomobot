import { useEffect } from 'react'

declare global {
  interface Window {
    adsbygoogle?: unknown[] & { pauseAdRequests?: 0 | 1 }
  }
}

/**
 * 데드엔드 화면(404/500/empty/error)에서는 AdSense 광고 요청을 중단한다.
 * https://support.google.com/adsense/answer/9183363 (Pause ad requests)
 */
export function useAdGate(hasContent: boolean) {
  useEffect(() => {
    window.adsbygoogle = window.adsbygoogle || []
    window.adsbygoogle.pauseAdRequests = hasContent ? 0 : 1
  }, [hasContent])
}
