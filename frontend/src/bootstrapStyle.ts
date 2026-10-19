// 웹/토스 진입점이 함께 쓰는 전역 스타일. 진입점마다 복사하면 어긋나므로 한 곳에 둔다.
export function injectGlobalStyle(): void {
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
}
