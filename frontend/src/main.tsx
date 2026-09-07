import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { NotFoundPage } from './components/NotFoundPage'
import { ServerErrorPage } from './components/ServerErrorPage'
import { ThemeProvider } from './ThemeContext'

const style = document.createElement('style')
style.textContent = `
  @keyframes fb-shimmer { 0%{background-position:-200px 0} 100%{background-position:240px 0} }
  @keyframes fb-spin { to{transform:rotate(360deg)} }
  @keyframes fb-pulse { 0%,100%{opacity:.45} 50%{opacity:.9} }
  @keyframes fb-draw { from{stroke-dashoffset:640} to{stroke-dashoffset:0} }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0B0D12; }
  ::-webkit-scrollbar { height: 8px; width: 8px; }
  ::-webkit-scrollbar-thumb { background: rgba(128,128,128,.25); border-radius: 8px; }
  input::placeholder { color: #9AA5B8; }
`
document.head.appendChild(style)

// 콘텐츠가 확인되기 전까지 AdSense 광고 요청을 중단한다 (데드엔드 화면 광고 노출 방지).
// https://support.google.com/adsense/answer/9183363
window.adsbygoogle = window.adsbygoogle || []
window.adsbygoogle.pauseAdRequests = 1

// 없는 경로는 Cloudflare Workers가 정적 404.html을 404 상태코드로 반환한다
// (wrangler.jsonc의 not_found_handling: "404-page"). 아래 분기는 index.html이
// 예상 밖의 경로에서 서빙될 때만 도달하는 방어선이다.
const path = window.location.pathname
const is500 = path === '/500'
const is404 = !is500 && path !== '/' && path !== '/index.html'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      {is500 ? <ServerErrorPage /> : is404 ? <NotFoundPage /> : <App />}
    </ThemeProvider>
  </StrictMode>,
)
