import { useEffect, useRef } from 'react'

// AdFit 관리자 페이지에서 발급받은 실제 스니펫과 대조 완료 (프로토콜 상대경로 포함, 그대로 사용).
const ADFIT_SCRIPT_SRC = '//t1.kakaocdn.net/kas/static/ba.min.js'

interface Adfit {
  display(unit: string): void
  destroy(unit: string): void
  refresh(unit: string): void
}

declare global {
  interface Window {
    adfit?: Adfit
  }
}

interface AdFitUnitProps {
  adUnit: string | undefined
  width: number
  height: number
  style?: React.CSSProperties
}

/**
 * 카카오 AdFit 배너 슬롯. adUnit이 비어있으면 아무것도 렌더하지 않는다.
 * ins/script는 AdFit이 발급한 스니펫과 1:1로 일치시킨다 — data-ad-onfail 등
 * 스니펫에 없는 속성을 추가하면 광고 요청이 실패할 수 있다는 공식 경고가 있어
 * 검증 안 된 확장은 넣지 않는다.
 *
 * ba.min.js는 자신이 실행되는 시점에 DOM에 있는 ins만 스캔하므로, 마운트마다
 * ins/script를 함께 새로 생성한다 (스크립트 재사용 시 새로 붙은 ins가 스캔되지 않음).
 * ba.min.js가 ins.style.display를 직접 조작하므로 React는 이 노드를 소유하지 않고
 * 빈 wrapper div만 렌더한다 — 무관한 리렌더로 스크립트가 만든 상태가 되돌아가는 것을 방지.
 * wrapper div의 고정 width/height(CLS 방지용)는 스니펫 바깥의 우리 자체 요소라 안전하다.
 */
export function AdFitUnit({ adUnit, width, height, style }: AdFitUnitProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!adUnit || !containerRef.current) return
    const container = containerRef.current

    const ins = document.createElement('ins')
    ins.className = 'kakao_ad_area'
    ins.style.display = 'none'
    ins.setAttribute('data-ad-unit', adUnit)
    ins.setAttribute('data-ad-width', String(width))
    ins.setAttribute('data-ad-height', String(height))
    container.appendChild(ins)

    const script = document.createElement('script')
    script.type = 'text/javascript'
    script.async = true
    script.src = ADFIT_SCRIPT_SRC
    container.appendChild(script)

    return () => {
      if (window.adfit?.destroy) {
        try {
          window.adfit.destroy(adUnit)
        } catch (e) {
          if (import.meta.env.DEV) console.warn('[AdFitUnit] destroy failed', e)
        }
      }
      ins.remove()
      script.remove()
    }
  }, [adUnit, width, height])

  if (!adUnit) return null

  return (
    <div
      ref={containerRef}
      style={{ width, height, overflow: 'hidden', ...style }}
    />
  )
}
