import { useC, useTheme } from '../ThemeContext'
import { FONT } from '../tokens'
import { PERIODS, RE_PERIODS, RE_REGIONS } from '../types'
import type { Lang, Market, Tab, ReLevel } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  lang: Lang
  tab: Tab
  market: Market
  periodIdx: number
  disclaimer: string
  t: Strings
  onLang: (l: Lang) => void
  onTab: (t: Tab) => void
  onMarket: (m: Market) => void
  onPeriod: (i: number) => void
  // RE controls
  reLevel: ReLevel
  reRegion: string
  rePeriodIdx: number
  onReLevel: (l: ReLevel) => void
  onReRegion: (r: string) => void
  onRePeriod: (i: number) => void
}

function SunIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
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
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M13.5 9.5A5.5 5.5 0 016.5 2.5a5.5 5.5 0 107 7z" />
    </svg>
  )
}

export function FomoHeader({
  lang, tab, market, periodIdx, disclaimer, t,
  onLang, onTab, onMarket, onPeriod,
  reLevel, reRegion, rePeriodIdx, onReLevel, onReRegion, onRePeriod,
}: Props) {
  const C = useC()
  const { theme, toggle } = useTheme()

  return (
    <div style={{ width: '100%', fontFamily: FONT.sans, background: C.surface, position: 'sticky', top: 0, zIndex: 10 }}>
      {/* Logo row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 16px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <img
            src="/icons/favicon.svg"
            alt="FomoBot Logo"
            style={{ width: 24, height: 24, flexShrink: 0, boxShadow: '0 0 0 1px rgba(62,123,250,0.3), 0 4px 14px rgba(62,123,250,0.4)', borderRadius: 8 }}
          />
          <div>
            <div style={{ fontSize: 16, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.02em', lineHeight: 1.05 }}>FomoBot</div>
            <div style={{ fontSize: 11, color: C.textDim, marginTop: 2, lineHeight: 1.1 }}>{t.tagline}</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={toggle}
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
            style={{
              width: 30, height: 30, border: `1px solid ${C.border}`, borderRadius: 8,
              background: C.surfaceUp, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: C.textMuted, flexShrink: 0,
            }}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <div style={{ display: 'flex', background: C.langBg, border: `1px solid ${C.langBorder}`, borderRadius: 9, padding: 2, gap: 2 }}>
            {(['ko', 'en'] as Lang[]).map((l) => (
              <button
                key={l}
                onClick={() => onLang(l)}
                style={{
                  padding: '5px 11px', border: 'none', borderRadius: 7,
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
      </div>

      {/* 주식 / 부동산 탭 */}
      <div style={{ padding: '0 16px 10px' }}>
        <div style={{ display: 'flex', gap: 4, background: C.surfaceAlt, border: `1px solid ${C.borderSub}`, borderRadius: 12, padding: 4 }}>
          {([
            { value: 'stock',      ko: '주식',   en: 'Stock' },
            { value: 'realestate', ko: '부동산', en: 'Real Estate' },
          ] as { value: Tab; ko: string; en: string }[]).map((item) => (
            <button
              key={item.value}
              onClick={() => onTab(item.value)}
              style={{
                flex: 1, textAlign: 'center', padding: '9px 0', border: 'none', borderRadius: 9,
                fontSize: 13, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer',
                background: tab === item.value ? 'linear-gradient(135deg,#3E7BFA,#2F66E0)' : 'transparent',
                color: tab === item.value ? '#fff' : C.textMuted,
                boxShadow: tab === item.value ? '0 2px 8px rgba(62,123,250,0.4)' : 'none',
              }}
            >
              {lang === 'ko' ? item.ko : item.en}
            </button>
          ))}
        </div>
      </div>

      {/* ── 주식 컨트롤 ── */}
      {tab === 'stock' && (
        <>
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
        </>
      )}

      {/* ── 부동산 컨트롤 ── */}
      {tab === 'realestate' && (
        <>
          {/* 지역 + 단위 한 줄 */}
          <div style={{ display: 'flex', gap: 6, padding: '0 16px 8px', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: 4, overflowX: 'auto', scrollbarWidth: 'none', flex: 1 }}>
              {RE_REGIONS.map((r) => (
                <button
                  key={r.value}
                  onClick={() => onReRegion(r.value)}
                  style={{
                    padding: '6px 11px', borderRadius: 9, border: 'none',
                    fontSize: 12, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
                    background: reRegion === r.value ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
                    color: reRegion === r.value ? C.blueSoft : C.textMuted,
                    outline: reRegion === r.value ? '1px solid rgba(62,123,250,0.32)' : 'none',
                  }}
                >
                  {r.label[lang]}
                </button>
              ))}
            </div>
            {/* 구/동 토글 */}
            <div style={{ display: 'flex', background: C.langBg, border: `1px solid ${C.langBorder}`, borderRadius: 8, padding: 2, gap: 2, flexShrink: 0 }}>
              {([
                { value: 'gu',   ko: '구', en: 'Gu' },
                { value: 'dong', ko: '동', en: 'Dong' },
              ] as { value: ReLevel; ko: string; en: string }[]).map((lv) => (
                <button
                  key={lv.value}
                  onClick={() => onReLevel(lv.value)}
                  style={{
                    padding: '5px 10px', border: 'none', borderRadius: 6,
                    fontSize: 11, fontWeight: 700, fontFamily: FONT.sans, cursor: 'pointer',
                    background: reLevel === lv.value ? C.langActive : 'transparent',
                    color: reLevel === lv.value ? C.textPrimary : C.textDim,
                  }}
                >
                  {lang === 'ko' ? lv.ko : lv.en}
                </button>
              ))}
            </div>
          </div>
          {/* RE 기간 탭 */}
          <div style={{ display: 'flex', gap: 6, padding: '0 16px 10px', overflowX: 'auto', scrollbarWidth: 'none' }}>
            {RE_PERIODS.map((p, i) => (
              <button
                key={p.value}
                onClick={() => onRePeriod(i)}
                style={{
                  padding: '6px 13px', borderRadius: 9, fontSize: 12, fontWeight: 600,
                  fontFamily: FONT.sans, cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
                  background: rePeriodIdx === i ? 'rgba(62,123,250,0.14)' : 'transparent',
                  color: rePeriodIdx === i ? C.blueSoft : C.textDim,
                  border: rePeriodIdx === i ? '1px solid rgba(62,123,250,0.32)' : '1px solid transparent',
                }}
              >
                {p.label[lang]}
              </button>
            ))}
          </div>
        </>
      )}

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
