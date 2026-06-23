import { C, FONT } from '../tokens'
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

export function FomoHeader({ lang, market, periodIdx, disclaimer, t, onLang, onMarket, onPeriod }: Props) {
  return (
    <div style={{ width: '100%', fontFamily: FONT.sans, background: C.surface, position: 'sticky', top: 0, zIndex: 10 }}>
      {/* Logo row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 16px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 24, height: 24, borderRadius: 8, flexShrink: 0,
            background: 'linear-gradient(135deg,#3E7BFA,#21D4D4)',
            boxShadow: '0 0 0 1px rgba(62,123,250,0.3),0 4px 14px rgba(62,123,250,0.4)',
          }} />
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.02em', lineHeight: 1.05 }}>FomoBot</div>
            <div style={{ fontSize: 11, color: C.textDim, marginTop: 2, lineHeight: 1.1 }}>{t.tagline}</div>
          </div>
        </div>

        {/* Lang toggle */}
        <div style={{ display: 'flex', background: '#11151D', border: `1px solid rgba(255,255,255,0.07)`, borderRadius: 9, padding: 2, gap: 2 }}>
          {(['ko', 'en'] as Lang[]).map((l) => (
            <button
              key={l}
              onClick={() => onLang(l)}
              style={{
                padding: '5px 11px', border: 'none', borderRadius: 7,
                fontSize: 11, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer', letterSpacing: '0.04em',
                background: lang === l ? '#2A3346' : 'transparent',
                color: lang === l ? C.textPrimary : C.textDim,
              }}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Market toggle */}
      <div style={{ padding: '0 16px' }}>
        <div style={{ display: 'flex', gap: 4, background: C.surfaceAlt, border: `1px solid ${C.borderSub}`, borderRadius: 12, padding: 4 }}>
          {(['kospi', 'nasdaq'] as Market[]).map((m) => (
            <button
              key={m}
              onClick={() => onMarket(m)}
              style={{
                flex: 1, textAlign: 'center', padding: '9px 0', border: 'none', borderRadius: 9,
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
      <div style={{ display: 'flex', gap: 6, padding: '12px 16px 10px', overflowX: 'auto', scrollbarWidth: 'none' }}>
        {PERIODS.map((p, i) => (
          <button
            key={p.value}
            onClick={() => onPeriod(i)}
            style={{
              padding: '6px 13px', borderRadius: 9, fontSize: 12, fontWeight: 600,
              fontFamily: FONT.sans, cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
              background: periodIdx === i ? 'rgba(62,123,250,0.14)' : 'transparent',
              color: periodIdx === i ? C.blueSoft : C.textDim,
              border: periodIdx === i ? '1px solid rgba(62,123,250,0.32)' : '1px solid transparent',
            }}
          >
            {p.label[lang]}
          </button>
        ))}
      </div>

      {/* Disclaimer banner */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        margin: '0 16px 12px', padding: '8px 10px',
        background: C.orangeFill, border: '1px solid rgba(244,169,60,0.16)', borderRadius: 9,
        fontSize: 11, color: '#B8924E', lineHeight: 1.35,
      }}>
        <span style={{ fontSize: 12, color: C.orange, flexShrink: 0 }}>⚠</span>
        <span>{disclaimer || t.disclaimer}</span>
      </div>
    </div>
  )
}
