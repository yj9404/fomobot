import { useEffect, useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import type { Lang } from '../types'

interface Props {
  url: string
  title: string
  lang: Lang
}

const STR = {
  ko: { label: '공유', copied: '링크를 복사했어요', failed: '링크를 복사하지 못했어요' },
  en: { label: 'Share', copied: 'Link copied', failed: 'Could not copy the link' },
} as const

/**
 * 공유 링크는 클릭한 시점에만 만든다(목록에서 /s/ 링크를 미리 노출하지 않음).
 * navigator.share → 미지원이거나 공유 시트 이외의 이유로 실패하면 클립보드 복사.
 */
export function ShareButton({ url, title, lang }: Props) {
  const C = useC()
  const t = STR[lang]
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 2000)
    return () => clearTimeout(id)
  }, [toast])

  async function handleClick() {
    if (typeof navigator.share === 'function') {
      try {
        await navigator.share({ title, url })
        return
      } catch (e) {
        // 사용자가 공유 시트를 닫은 것 — 아무것도 하지 않는다.
        if (e instanceof DOMException && e.name === 'AbortError') return
        // NotAllowedError 등은 클립보드로 폴백
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setToast(t.copied)
    } catch {
      setToast(t.failed)
    }
  }

  return (
    <>
      <button
        onClick={handleClick}
        style={{
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '5px 11px', borderRadius: 7, fontSize: 11.5, fontWeight: 700,
          fontFamily: FONT.sans, cursor: 'pointer',
          background: 'rgba(62,123,250,0.15)', color: C.blueSoft,
          border: '1px solid rgba(62,123,250,0.35)',
        }}
      >
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 10V2" />
          <path d="M5 5l3-3 3 3" />
          <path d="M3 9v4a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V9" />
        </svg>
        {t.label}
      </button>
      {toast && (
        <div
          role="status"
          aria-live="polite"
          style={{
            position: 'fixed', left: '50%', bottom: 28, transform: 'translateX(-50%)',
            zIndex: 1000, padding: '10px 16px', borderRadius: 10,
            background: C.textPrimary, color: C.surface,
            fontSize: 13, fontWeight: 600, fontFamily: FONT.sans,
            boxShadow: '0 8px 24px rgba(0,0,0,0.25)', whiteSpace: 'nowrap',
          }}
        >
          {toast}
        </div>
      )}
    </>
  )
}
