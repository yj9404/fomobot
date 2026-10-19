import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import TossApp from './TossApp'
import { injectGlobalStyle } from './bootstrapStyle'
import { ThemeProvider } from './ThemeContext'

// 앱인토스 미니앱 진입점. 웹 진입점(main.tsx)과 달리 App 대신 토스 전용 셸(TossApp)을 렌더링하고
// 공유 랜딩/404/500 경로 분기와 AdSense 코드가 없다. 토스는 라이트 모드만 지원하므로 테마를 light로 고정한다.
injectGlobalStyle()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider fixedTheme="light">
      <TossApp />
    </ThemeProvider>
  </StrictMode>,
)
