import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

const style = document.createElement('style')
style.textContent = `
  @keyframes fb-shimmer { 0%{background-position:-200px 0} 100%{background-position:240px 0} }
  @keyframes fb-spin { to{transform:rotate(360deg)} }
  @keyframes fb-pulse { 0%,100%{opacity:.45} 50%{opacity:.9} }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0B0D12; }
  ::-webkit-scrollbar { height: 8px; width: 8px; }
  ::-webkit-scrollbar-thumb { background: rgba(255,255,255,.12); border-radius: 8px; }
`
document.head.appendChild(style)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
