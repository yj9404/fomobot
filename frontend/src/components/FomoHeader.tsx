import { useState, useRef, useEffect, useCallback } from 'react'
import { useC, useTheme } from '../ThemeContext'
import { FONT } from '../tokens'
import { PERIODS, RE_PERIODS, RE_REGIONS } from '../types'
import { useReRegionSearch } from '../hooks/useReRegionSearch'
import type { Lang, Market, Tab, RegionItem } from '../types'
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
  reRegion: string
  rePeriodIdx: number
  reGu: string
  reDong: string
  onReRegion: (r: string) => void
  onRePeriod: (i: number) => void
  onReGu: (gu: string, dong: string) => void
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

function RegionSearchMobile({
  lang, reGu, reDong, onReGu,
}: {
  lang: Lang
  reGu: string
  reDong: string
  onReGu: (gu: string, dong: string) => void
}) {
  const C = useC()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [selectedLabel, setSelectedLabel] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  const { results, loading } = useReRegionSearch(open ? q : '')

  const grouped = (() => {
    const seen = new Set<string>()
    const items: Array<{ type: 'gu' | 'dong'; item: RegionItem }> = []
    for (const r of results) {
      if (!seen.has(r.sigungu_code)) {
        seen.add(r.sigungu_code)
        items.push({ type: 'gu', item: r })
      }
    }
    for (const r of results) {
      items.push({ type: 'dong', item: r })
    }
    return items
  })()

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSelect = useCallback((item: RegionItem, type: 'gu' | 'dong') => {
    const dong = type === 'dong' ? item.eupmyeondong : ''
    onReGu(item.sigungu_code, dong)
    setSelectedLabel(dong ? `${item.sido_name} ${item.sigungu_name} ${dong}` : `${item.sido_name} ${item.sigungu_name} 전체`)
    setQ('')
    setOpen(false)
  }, [onReGu])

  const handleClear = useCallback(() => {
    onReGu('', '')
    setQ('')
    setOpen(false)
    setSelectedLabel('')
  }, [onReGu])

  // 칩 형태 (선택 완료)
  if (reGu && !open) {
    const chipLabel = selectedLabel || (reDong ? `${reGu} ${reDong}` : `${reGu} 전체`)
    return (
      <div ref={containerRef} style={{ padding: '0 16px 8px' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '5px 10px',
          background: 'rgba(62,123,250,0.12)',
          border: '1px solid rgba(62,123,250,0.3)',
          borderRadius: 8, cursor: 'pointer',
          maxWidth: '100%',
        }}
          onClick={() => { setOpen(true); setQ('') }}
        >
          <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke={C.blueSoft} strokeWidth="1.8" strokeLinecap="round">
            <path d="M8 2C5.8 2 4 3.8 4 6c0 3.5 4 8 4 8s4-4.5 4-8c0-2.2-1.8-4-4-4z" />
            <circle cx="8" cy="6" r="1.5" />
          </svg>
          <span style={{ fontSize: 12, color: C.blueSoft, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {chipLabel}
          </span>
          <button
            onMouseDown={(e) => { e.stopPropagation(); handleClear() }}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: C.blueSoft, fontSize: 12, padding: 0, lineHeight: 1, flexShrink: 0 }}
          >
            ✕
          </button>
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ padding: '0 16px 8px', position: 'relative' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7,
        background: C.surfaceAlt,
        border: `1px solid ${open ? 'rgba(62,123,250,0.45)' : C.borderSub}`,
        borderRadius: 8, padding: '7px 12px',
        transition: 'border-color 0.15s',
      }}>
        <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke={C.textDim} strokeWidth="1.8" strokeLinecap="round">
          <circle cx="6.5" cy="6.5" r="4.5" />
          <line x1="10.5" y1="10.5" x2="14" y2="14" />
        </svg>
        <input
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          placeholder={lang === 'ko' ? '구/동 검색…' : 'Search district…'}
          style={{
            flex: 1, border: 'none', outline: 'none',
            background: 'transparent', fontSize: 12,
            color: C.textPrimary, fontFamily: FONT.sans,
          }}
        />
        {q && (
          <button
            onClick={() => setQ('')}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: C.textMuted, fontSize: 12, padding: 0 }}
          >
            ✕
          </button>
        )}
      </div>

      {open && q.length > 0 && (
        <div style={{
          position: 'absolute', left: 16, right: 16, top: 'calc(100% - 2px)',
          background: C.surface,
          border: '1.5px solid rgba(62,123,250,0.28)',
          borderRadius: 9, boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
          zIndex: 100, overflow: 'hidden', maxHeight: 200, overflowY: 'auto',
        }}>
          {loading && (
            <div style={{ padding: '10px 12px', fontSize: 11, color: C.textDim }}>
              {lang === 'ko' ? '검색 중…' : 'Searching…'}
            </div>
          )}
          {!loading && grouped.length === 0 && (
            <div style={{ padding: '10px 12px', fontSize: 11, color: C.textDim }}>
              {lang === 'ko' ? '결과 없음' : 'No results'}
            </div>
          )}
          {grouped.map(({ type, item }, idx) => (
            <div
              key={`${type}-${item.sigungu_code}-${item.eupmyeondong}-${idx}`}
              onMouseDown={(e) => { e.preventDefault(); handleSelect(item, type) }}
              style={{
                padding: type === 'gu' ? '8px 12px 6px' : '6px 12px 6px 20px',
                cursor: 'pointer',
                borderBottom: `1px solid ${C.borderFaint}`,
                background: 'transparent',
                transition: 'background 0.1s',
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = C.hoverBg }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = 'transparent' }}
            >
              {type === 'gu' ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: C.textPrimary }}>
                    {item.sido_name} {item.sigungu_name}
                  </span>
                  <span style={{
                    fontSize: 10, color: C.blueSoft,
                    background: 'rgba(62,123,250,0.1)', padding: '1px 5px', borderRadius: 4,
                  }}>
                    {lang === 'ko' ? '전체' : 'All'}
                  </span>
                </div>
              ) : (
                <div style={{ fontSize: 11, color: C.textMuted }}>
                  {item.eupmyeondong}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function FomoHeader({
  lang, tab, market, periodIdx, disclaimer, t,
  onLang, onTab, onMarket, onPeriod,
  reRegion, rePeriodIdx, reGu, reDong,
  onReRegion, onRePeriod, onReGu,
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
          {/* 지역(sido) */}
          <div style={{ display: 'flex', gap: 4, padding: '0 16px 6px', overflowX: 'auto', scrollbarWidth: 'none' }}>
            {RE_REGIONS.map((r) => (
              <button
                key={r.value}
                onClick={() => onReRegion(r.value)}
                style={{
                  padding: '6px 11px', borderRadius: 9, border: 'none',
                  fontSize: 12, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', whiteSpace: 'nowrap', flexShrink: 0,
                  background: reRegion === r.value && !reGu ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
                  color: reRegion === r.value && !reGu ? C.blueSoft : C.textMuted,
                  outline: reRegion === r.value && !reGu ? '1px solid rgba(62,123,250,0.32)' : 'none',
                }}
              >
                {r.label[lang]}
              </button>
            ))}
          </div>

          {/* 구/동 세부 검색 (모바일) */}
          <RegionSearchMobile
            lang={lang}
            reGu={reGu}
            reDong={reDong}
            onReGu={onReGu}
          />

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
