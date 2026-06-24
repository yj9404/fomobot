import { useC, useTheme } from '../ThemeContext'
import { FONT } from '../tokens'
import { PERIODS } from '../types'
import type { Lang, Market } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  lang: Lang
  market: Market
  periodIdx: number
  disclaimer: string
  t: Strings
  onLang: (l: Lang) => void
  onMarket: (m: Market) => void
  onPeriod: (i: number) => void
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
      <circle cx="8" cy="8" r="2.8" />
      <line x1="8" y1="1.2" x2="8" y2="2.8" />
      <line x1="8" y1="13.2" x2="8" y2="14.8" />
      <line x1="1.2" y1="8" x2="2.8" y2="8" />
      <line x1="13.2" y1="8" x2="14.8" y2="8" />
      <line x1="3.1" y1="3.1" x2="4.2" y2="4.2" />
      <line x1="11.8" y1="11.8" x2="12.9" y2="12.9" />
      <line x1="12.9" y1="3.1" x2="11.8" y2="4.2" />
      <line x1="4.2" y1="11.8" x2="3.1" y2="12.9" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13.5 9.5A5.5 5.5 0 016.5 2.5a5.5 5.5 0 107 7z" />
    </svg>
  )
}

export function NavRail({ lang, market, periodIdx, disclaimer, t, onLang, onMarket, onPeriod }: Props) {
  const C = useC()
  const { theme, toggle } = useTheme()

  return (
    <div style={{
      width: 220,
      flexShrink: 0,
      background: C.surface,
      borderRight: `1px solid ${C.borderSub}`,
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 16px 20px',
      gap: 22,
      position: 'sticky',
      top: 0,
      height: '100vh',
      overflowY: 'auto',
      scrollbarWidth: 'thin',
      fontFamily: FONT.sans,
    }}>
      {/* Logo + theme toggle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <img
          src="/icons/favicon.svg"
          alt="FomoBot Logo"
          style={{
            width: 28,
            height: 28,
            flexShrink: 0,
            boxShadow: '0 0 0 1px rgba(62,123,250,0.3), 0 4px 14px rgba(62,123,250,0.4)',
            borderRadius: 9,
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 17, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.02em', lineHeight: 1.05 }}>FomoBot</div>
          <div style={{ fontSize: 10, color: C.textDim, marginTop: 3, lineHeight: 1.3 }}>{t.tagline}</div>
        </div>
        <button
          onClick={toggle}
          title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          style={{
            width: 30, height: 30, flexShrink: 0,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            background: C.surfaceUp,
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: C.textMuted,
          }}
        >
          {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
        </button>
      </div>

      {/* Lang toggle */}
      <div>
        <div style={sectionLabel(C)}>Language</div>
        <div style={{ display: 'flex', background: C.langBg, border: `1px solid ${C.langBorder}`, borderRadius: 9, padding: 2, gap: 2 }}>
          {(['ko', 'en'] as Lang[]).map((l) => (
            <button
              key={l}
              onClick={() => onLang(l)}
              style={{
                flex: 1, padding: '6px 0', border: 'none', borderRadius: 7,
                fontSize: 11, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer', letterSpacing: '0.04em',
                background: lang === l ? C.langActive : 'transparent',
                color: lang === l ? C.textPrimary : C.textDim,
              }}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Market toggle */}
      <div>
        <div style={sectionLabel(C)}>Market</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, background: C.surfaceAlt, border: `1px solid ${C.borderSub}`, borderRadius: 12, padding: 4 }}>
          {(['kospi', 'nasdaq'] as Market[]).map((m) => (
            <button
              key={m}
              onClick={() => onMarket(m)}
              style={{
                width: '100%', textAlign: 'center', padding: '9px 0', border: 'none', borderRadius: 9,
                fontSize: 13, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer',
                background: market === m ? 'linear-gradient(135deg,#3E7BFA,#2F66E0)' : 'transparent',
                color: market === m ? '#fff' : C.textMuted,
                boxShadow: market === m ? '0 2px 8px rgba(62,123,250,0.4)' : 'none',
              }}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Period tabs */}
      <div>
        <div style={sectionLabel(C)}>Period</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {PERIODS.map((p, i) => (
            <button
              key={p.value}
              onClick={() => onPeriod(i)}
              style={{
                width: '100%', padding: '8px 12px', borderRadius: 9,
                fontSize: 13, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', textAlign: 'left',
                background: periodIdx === i ? 'rgba(62,123,250,0.14)' : 'transparent',
                color: periodIdx === i ? C.blueSoft : C.textDim,
                border: periodIdx === i ? '1px solid rgba(62,123,250,0.32)' : '1px solid transparent',
              }}
            >
              {p.label[lang]}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1 }} />

      {/* Disclaimer */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: 7,
        padding: '9px 10px',
        background: C.orangeFill, border: '1px solid rgba(244,169,60,0.16)', borderRadius: 9,
        fontSize: 10.5, color: '#B8924E', lineHeight: 1.4,
      }}>
        <span style={{ fontSize: 12, color: C.orange, flexShrink: 0 }}>⚠</span>
        <span>{disclaimer || t.disclaimer}</span>
      </div>
    </div>
  )
}

function sectionLabel(C: ReturnType<typeof useC>): React.CSSProperties {
  return {
    fontSize: 10,
    fontWeight: 600,
    color: C.textDim,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginBottom: 8,
  }
}
