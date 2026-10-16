import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { buildShareData } from '../../shared/share'
import type { Lang } from '../types'

const STR = {
  ko: {
    label: '공유', copied: '링크를 복사했어요', failed: '링크를 복사하지 못했어요',
    imageLabel: '이미지로 공유', imageLoading: '이미지 준비 중…',
    imageRetry: '이미지가 준비됐어요. 한 번 더 눌러 주세요', imageFailed: '이미지를 불러오지 못했어요',
  },
  en: {
    label: 'Share', copied: 'Link copied', failed: 'Could not copy the link',
    imageLabel: 'Share image', imageLoading: 'Preparing…',
    imageRetry: 'Image ready. Tap again to share', imageFailed: 'Could not load the image',
  },
} as const

function useToast(): [string | null, (msg: string) => void] {
  const [toast, setToast] = useState<string | null>(null)
  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 2000)
    return () => clearTimeout(id)
  }, [toast])
  return [toast, setToast]
}

function isAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === 'AbortError'
}

function PillButton({ onClick, disabled, icon, children }: {
  onClick: () => void; disabled?: boolean; icon: ReactNode; children: ReactNode
}) {
  const C = useC()
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '5px 11px', borderRadius: 7, fontSize: 11.5, fontWeight: 700,
        fontFamily: FONT.sans, cursor: disabled ? 'default' : 'pointer', opacity: disabled ? 0.6 : 1,
        background: 'rgba(62,123,250,0.15)', color: C.blueSoft,
        border: '1px solid rgba(62,123,250,0.35)',
      }}
    >
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {icon}
      </svg>
      {children}
    </button>
  )
}

function Toast({ message }: { message: string | null }) {
  const C = useC()
  if (!message) return null
  return (
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
      {message}
    </div>
  )
}

interface ShareProps {
  url: string
  /** 공유 문구(URL 제외) — shared/share.shareText로 만든다 */
  text: string
  lang: Lang
  /** 기본 "공유" 대신 쓸 버튼 문구 */
  label?: string
}

/**
 * 링크 공유. 공유 링크는 클릭한 시점에만 만든다(목록에서 /s/ 링크를 미리 노출하지 않음).
 * navigator.share → 미지원이거나 공유 시트 이외의 이유로 실패하면 클립보드 복사.
 */
export function ShareButton({ url, text, lang, label }: ShareProps) {
  const t = STR[lang]
  const [toast, setToast] = useToast()

  async function handleClick() {
    if (typeof navigator.share === 'function') {
      try {
        // 플랫폼마다 공유 대상이 쓰는 필드가 달라 buildShareData가 나눈다(Windows는 url만 넘김).
        await navigator.share(buildShareData(text, url, navigator.userAgent))
        return
      } catch (e) {
        // 사용자가 공유 시트를 닫은 것 — 아무것도 하지 않는다.
        if (isAbort(e)) return
        // NotAllowedError 등은 클립보드로 폴백
      }
    }
    try {
      await navigator.clipboard.writeText(`${text}\n${url}`)
      setToast(t.copied)
    } catch {
      setToast(t.failed)
    }
  }

  return (
    <>
      <PillButton onClick={handleClick} icon={<><path d="M8 10V2" /><path d="M5 5l3-3 3 3" /><path d="M3 9v4a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V9" /></>}>
        {label ?? t.label}
      </PillButton>
      <Toast message={toast} />
    </>
  )
}

interface ShareImageProps {
  /** 카드 PNG 경로 — shared/share.cardImagePath */
  imageUrl: string
  /** shared/share.cardFileName */
  fileName: string
  lang: Lang
}

/** 이 브라우저가 이미지 파일 공유를 지원하는가(카카오톡 인앱·Firefox 등은 미지원). */
function canShareImageFiles(): boolean {
  if (typeof navigator.canShare !== 'function') return false
  try {
    return navigator.canShare({ files: [new File([''], 'card.png', { type: 'image/png' })] })
  } catch {
    return false
  }
}

/**
 * 카드 이미지 공유. 이미지는 클릭할 때 받는다 — 조회 결과마다 미리 받으면 보기만 해도
 * 카드가 생성돼 R2·backend 부하가 생긴다. 받는 사이에 사용자 제스처가 만료되면(Safari)
 * 공유가 NotAllowedError로 거부되는데, 이때 받아 둔 이미지를 유지하고 한 번 더 누르게 한다.
 * 파일 공유를 지원하지 않는 브라우저에서는 버튼을 숨긴다.
 */
export function ShareImageButton({ imageUrl, fileName, lang }: ShareImageProps) {
  const t = STR[lang]
  const supported = useMemo(canShareImageFiles, [])
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useToast()

  // 다른 종목·기간으로 바뀌면 받아 둔 이미지를 버린다.
  useEffect(() => { setFile(null) }, [imageUrl])

  if (!supported) return null

  async function handleClick() {
    let f = file
    if (!f) {
      setLoading(true)
      try {
        const res = await fetch(imageUrl)
        if (!res.ok || !(res.headers.get('content-type') ?? '').startsWith('image/png')) throw new Error('bad image')
        f = new File([await res.blob()], fileName, { type: 'image/png' })
        setFile(f)
      } catch {
        setToast(t.imageFailed)
        return
      } finally {
        setLoading(false)
      }
    }
    try {
      await navigator.share({ files: [f] })
    } catch (e) {
      if (isAbort(e)) return
      if (e instanceof DOMException && e.name === 'NotAllowedError') setToast(t.imageRetry)
      else setToast(t.imageFailed)
    }
  }

  return (
    <>
      <PillButton
        onClick={handleClick}
        disabled={loading}
        icon={<><rect x="2" y="3" width="12" height="10" rx="1.5" /><circle cx="6" cy="7" r="1.2" /><path d="M14 11l-3.5-3.5L5 13" /></>}
      >
        {loading ? t.imageLoading : t.imageLabel}
      </PillButton>
      <Toast message={toast} />
    </>
  )
}
