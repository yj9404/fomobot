import { useEffect, useRef, useState } from 'react'
import { useC } from '../ThemeContext'
import type { Strings } from '../i18n/strings'

interface Props {
  t: Strings
}

/**
 * halt_resumption=true 카드/행에 붙는 ⓘ 아이콘 — hover가 없는 모바일 대응으로
 * tap(클릭)으로 여닫는다. 아이콘 클릭은 stopPropagation해 부모 행/버튼의
 * onClick(카드 토글, 종목 선택 등)으로 번지지 않게 막고, 바깥 아무 곳이나
 * 탭하면 document mousedown 리스너로 닫는다(StockSearchArea의 outside-click
 * 패턴과 동일). 팝오버 라이브러리 없이 useState 하나로만 상태를 관리한다.
 *
 * 이 컴포넌트는 절대위치 플로팅 박스로 뜬다(RankingTable처럼 조상에
 * overflow:hidden이 없는 곳 전용). RankingCard처럼 조상 카드가
 * overflow:hidden이라 플로팅 박스가 잘리는 곳에서는 이 컴포넌트를 쓰지
 * 말고, 카드 내부에 인라인으로 확장되는 블록을 직접 구현할 것.
 */
export function HaltResumptionInfo({ t }: Props) {
  const C = useC()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    // 'click'을 쓴다(mousedown 아님) — RankingCard의 인라인 확장판에서
    // mousedown이 레이아웃 시프트와 겹쳐 다른 행의 클릭을 놓치는 버그가
    // 실측됐다. 여기는 플로팅 박스라 레이아웃 시프트는 없지만, 두 컴포넌트가
    // 다른 이벤트를 쓰면 동작이 미묘하게 갈릴 수 있어 동일하게 맞춘다.
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [open])

  return (
    <span ref={containerRef} style={{ position: 'relative', display: 'inline-flex', flexShrink: 0 }}>
      <span
        onClick={(e) => {
          e.stopPropagation()
          e.preventDefault()
          setOpen((v) => !v)
        }}
        style={{ fontSize: 12, lineHeight: 1, cursor: 'pointer', color: C.textDim, padding: 2 }}
      >
        ⓘ
      </span>
      {open && (
        <span
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'absolute', top: '100%', right: 0, marginTop: 6,
            width: 220, maxWidth: '70vw', zIndex: 20,
            display: 'block', padding: '10px 12px', boxSizing: 'border-box',
            background: C.surface, border: `1px solid ${C.cardBorderDefault}`,
            borderRadius: 10, boxShadow: '0 4px 16px rgba(0,0,0,0.18)',
            fontSize: 11.5, lineHeight: 1.5, color: C.textPrimary,
            textAlign: 'left', fontWeight: 400, whiteSpace: 'normal',
          }}
        >
          {t.haltResumptionTitle}
        </span>
      )}
    </span>
  )
}
