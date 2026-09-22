import { useEffect, useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import type { Lang } from '../types'

export const FOOTER_LINKS = [
  { href: '/about.html', ko: '소개', en: 'About' },
  { href: '/articles.html', ko: '읽을거리', en: 'Articles' },
  { href: '/methodology.html', ko: '방법론', en: 'Methodology' },
  { href: '/survivorship-bias.html', ko: '생존 편향', en: 'Survivorship bias' },
  { href: '/glossary.html', ko: '용어 해설', en: 'Glossary' },
  { href: '/privacy.html', ko: '개인정보처리방침', en: 'Privacy' },
]

const CONTACT_EMAIL = 'yjlee.k94@gmail.com'

const CONTACT = {
  ko: {
    label: '버그 및 기능 문의',
    subject: '[FomoBot] 버그/기능 문의',
    title: '메일 앱이 열리지 않았나요?',
    desc: '이 브라우저에 연결된 메일 앱이 없는 것 같아요. 아래 주소로 보내주세요.',
    copy: '주소 복사',
    copied: '복사됨',
    gmail: 'Gmail로 작성',
    retry: '메일 앱으로 다시 시도',
    close: '닫기',
  },
  en: {
    label: 'Report a Bug or Feature',
    subject: '[FomoBot] Bug/Feature Request',
    title: "Mail app didn't open?",
    desc: 'No mail app seems to be linked to this browser. Please write to the address below.',
    copy: 'Copy address',
    copied: 'Copied',
    gmail: 'Compose in Gmail',
    retry: 'Try the mail app again',
    close: 'Close',
  },
} as const

const mailtoHref = (lang: Lang) =>
  `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(CONTACT[lang].subject)}`

const gmailHref = (lang: Lang) =>
  `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(CONTACT_EMAIL)}` +
  `&su=${encodeURIComponent(CONTACT[lang].subject)}`

export function Footer({ lang, style }: { lang: Lang; style?: React.CSSProperties }) {
  const C = useC()
  const [fallbackOpen, setFallbackOpen] = useState(false)
  const t = CONTACT[lang]

  /**
   * mailto:는 OS에 메일 핸들러가 등록돼 있지 않으면(기본 메일 앱을 한 번도
   * 지정하지 않은 Windows/크롬 데스크톱이 흔하다) 클릭해도 아무 반응 없이
   * 조용히 실패한다. 실패를 직접 감지하는 API는 없어서, 메일 앱이 뜨면
   * 브라우저 창이 포커스를 잃는다는 점(blur/visibilitychange)을 신호로 쓴다.
   * 1.2초 안에 아무 신호도 없으면 핸들러가 없다고 보고 폴백 안내를 띄운다.
   * 오탐(앱은 떴는데 blur가 안 잡힘)이 나도 안내 패널이 하나 더 뜰 뿐이라
   * 기존 동작(모바일·메일 앱 있는 PC)은 그대로 둔다.
   */
  const handleContactClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    // 새 탭/창으로 열려는 클릭은 건드리지 않는다.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return

    let left = false
    const mark = () => { left = true }
    window.addEventListener('blur', mark, { once: true })
    document.addEventListener('visibilitychange', mark, { once: true })

    window.setTimeout(() => {
      window.removeEventListener('blur', mark)
      document.removeEventListener('visibilitychange', mark)
      if (!left) setFallbackOpen(true)
    }, 1200)
  }

  return (
    <>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 10px', fontSize: 10.5, ...style }}>
        {FOOTER_LINKS.map((l) => (
          <a key={l.href} href={l.href} style={{ color: C.textDim, textDecoration: 'none' }}>
            {lang === 'ko' ? l.ko : l.en}
          </a>
        ))}
        <a
          href={mailtoHref(lang)}
          onClick={handleContactClick}
          style={{ color: C.textDim, textDecoration: 'none' }}
        >
          {t.label}
        </a>
      </div>
      {fallbackOpen && <ContactFallback lang={lang} onClose={() => setFallbackOpen(false)} />}
    </>
  )
}

function ContactFallback({ lang, onClose }: { lang: Lang; onClose: () => void }) {
  const C = useC()
  const [copied, setCopied] = useState(false)
  const t = CONTACT[lang]

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const copyEmail = async () => {
    try {
      await navigator.clipboard.writeText(CONTACT_EMAIL)
      setCopied(true)
      return
    } catch {
      // clipboard API가 막힌 환경(비보안 컨텍스트, 구형 브라우저) 대비
    }
    const ta = document.createElement('textarea')
    ta.value = CONTACT_EMAIL
    ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0'
    document.body.appendChild(ta)
    ta.select()
    try { document.execCommand('copy'); setCopied(true) } catch { /* 복사 불가 — 주소는 화면에 보인다 */ }
    document.body.removeChild(ta)
  }

  const btn: React.CSSProperties = {
    padding: '7px 12px', borderRadius: 6, fontSize: 11.5, fontFamily: FONT.sans,
    border: `1px solid ${C.border}`, background: C.surfaceUp, color: C.textSub,
    cursor: 'pointer', textDecoration: 'none', display: 'inline-block',
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%', maxWidth: 340, boxSizing: 'border-box',
          background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10,
          padding: 18, fontFamily: FONT.sans,
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 600, color: C.textPrimary, marginBottom: 6 }}>
          {t.title}
        </div>
        <div style={{ fontSize: 11.5, color: C.textMuted, lineHeight: 1.5, marginBottom: 12 }}>
          {t.desc}
        </div>
        <div style={{
          fontFamily: FONT.mono, fontSize: 12, color: C.textPrimary,
          background: C.surfaceAlt, border: `1px solid ${C.borderSub}`, borderRadius: 6,
          padding: '8px 10px', marginBottom: 12, wordBreak: 'break-all',
        }}>
          {CONTACT_EMAIL}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <button type="button" onClick={copyEmail} style={btn}>
            {copied ? `✓ ${t.copied}` : t.copy}
          </button>
          <a href={gmailHref(lang)} target="_blank" rel="noopener noreferrer" style={btn}>
            {t.gmail}
          </a>
          <a href={mailtoHref(lang)} style={btn}>
            {t.retry}
          </a>
          <button
            type="button"
            onClick={onClose}
            style={{ ...btn, background: 'transparent', border: 'none', color: C.textDim, marginLeft: 'auto' }}
          >
            {t.close}
          </button>
        </div>
      </div>
    </div>
  )
}
