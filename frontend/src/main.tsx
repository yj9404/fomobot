import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { injectGlobalStyle } from './bootstrapStyle'
import { NotFoundPage } from './components/NotFoundPage'
import { ServerErrorPage } from './components/ServerErrorPage'
import { SharePage } from './components/SharePage'
import { ThemeProvider } from './ThemeContext'

injectGlobalStyle()

// 콘텐츠가 확인되기 전까지 AdSense 광고 요청을 중단한다 (데드엔드 화면 광고 노출 방지).
// https://support.google.com/adsense/answer/9183363
window.adsbygoogle = window.adsbygoogle || []
window.adsbygoogle.pauseAdRequests = 1

// 없는 경로는 Cloudflare Workers가 정적 404.html을 404 상태코드로 반환한다
// (wrangler.jsonc의 not_found_handling: "404-page"). 아래 분기는 index.html이
// 예상 밖의 경로에서 서빙될 때만 도달하는 방어선이다.
// /s/{market}/{ticker}는 Worker(worker/index.ts)가 OG 메타를 주입한 index.html을 내려준다.
const path = window.location.pathname
const is500 = path === '/500'
const isShare = /^\/s\/[^/]+\/[^/]+\/?$/.test(path)
const is404 = !is500 && !isShare && path !== '/' && path !== '/index.html'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      {is500 ? <ServerErrorPage /> : isShare ? <SharePage /> : is404 ? <NotFoundPage /> : <App />}
    </ThemeProvider>
  </StrictMode>,
)
