import { useState, useRef, useEffect, useCallback } from 'react'
import { useC, useTheme } from '../ThemeContext'
import { FONT, DECLINE_ACCENT_DARK, DECLINE_ACCENT_LIGHT } from '../tokens'
import { PERIODS, RE_PERIODS, RE_REGIONS, CAP_TIERS } from '../types'
import { useReRegionSearch } from '../hooks/useReRegionSearch'
import { useReSegments } from '../hooks/useReSegments'
import { Footer } from './Footer'
import type { Lang, Market, OrderDir, Tab, RegionItem, CapTier } from '../types'
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
  capTier: CapTier
  onCapTier: (c: CapTier) => void
  stockOrder: OrderDir
  onStockOrder: (o: OrderDir) => void
  // RE controls
  reRegion: string
  rePeriodIdx: number
  reGu: string
  reDong: string
  reSeg: string
  reMinPrice: number | null
  reMaxPrice: number | null
  reOrder: OrderDir
  onReOrder: (o: OrderDir) => void
  onReRegion: (r: string) => void
  onRePeriod: (i: number) => void
  onReGu: (gu: string, dong: string) => void
  onReSeg: (seg: string) => void
  onReMinPrice: (v: number | null) => void
  onReMaxPrice: (v: number | null) => void
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

function RegionSearch({
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

  // 그룹화: sigungu별로 unique gu 옵션 + 개별 dong 옵션
  const grouped = (() => {
    const byGu = new Map<string, RegionItem[]>()
    for (const r of results) {
      if (!byGu.has(r.sigungu_code)) {
        byGu.set(r.sigungu_code, [])
      }
      byGu.get(r.sigungu_code)!.push(r)
    }

    const items: Array<{ type: 'gu' | 'dong'; item: RegionItem }> = []
    for (const dongs of byGu.values()) {
      if (dongs.length > 0) {
        items.push({ type: 'gu', item: dongs[0] })
        for (const r of dongs) {
          items.push({ type: 'dong', item: r })
        }
      }
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

  // 선택된 구/동 칩
  if (reGu && !open) {
    const chipLabel = selectedLabel || (reDong ? `${reGu} ${reDong}` : `${reGu} 전체`)
    return (
      <div ref={containerRef} style={{ marginTop: 6 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 10px',
          background: 'rgba(62,123,250,0.12)',
          border: '1px solid rgba(62,123,250,0.3)',
          borderRadius: 8, cursor: 'pointer',
        }}
          onClick={() => { setOpen(true); setQ('') }}
        >
          <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke={C.blueSoft} strokeWidth="1.8" strokeLinecap="round">
            <path d="M8 2C5.8 2 4 3.8 4 6c0 3.5 4 8 4 8s4-4.5 4-8c0-2.2-1.8-4-4-4z" />
            <circle cx="8" cy="6" r="1.5" />
          </svg>
          <span style={{ flex: 1, fontSize: 12, color: C.blueSoft, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {chipLabel}
          </span>
          <button
            onMouseDown={(e) => { e.stopPropagation(); handleClear() }}
            style={{
              border: 'none', background: 'transparent',
              cursor: 'pointer', color: C.blueSoft,
              fontSize: 12, padding: 0, lineHeight: 1,
              flexShrink: 0,
            }}
          >
            ✕
          </button>
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ marginTop: 6, position: 'relative' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7,
        background: C.inputBg,
        border: `1.5px solid ${open ? 'rgba(62,123,250,0.65)' : C.inputBorder}`,
        borderRadius: 8, padding: '7px 10px',
        transition: 'border-color 0.15s',
      }}>
        <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke={C.textMuted} strokeWidth="1.8" strokeLinecap="round">
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
          position: 'absolute', left: 0, right: 0, top: 'calc(100% + 2px)',
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

export function NavRail({
  lang, tab, market, periodIdx, disclaimer, t,
  onLang, onTab, onMarket, onPeriod, capTier, onCapTier,
  stockOrder, onStockOrder,
  reRegion, rePeriodIdx, reGu, reDong, reSeg, reMinPrice, reMaxPrice,
  reOrder, onReOrder,
  onReRegion, onRePeriod, onReGu, onReSeg, onReMinPrice, onReMaxPrice,
}: Props) {
  const segments = useReSegments()
  const C = useC()
  const { theme, toggle, atmosphereMode } = useTheme()
  const da = theme === 'dark' ? DECLINE_ACCENT_DARK : DECLINE_ACCENT_LIGHT
  const isFall = atmosphereMode === 'fall'
  const [minStr, setMinStr] = useState(() => reMinPrice != null ? String(reMinPrice) : '')
  const [maxStr, setMaxStr] = useState(() => reMaxPrice != null ? String(reMaxPrice) : '')

  useEffect(() => { if (reMinPrice == null) setMinStr('') }, [reMinPrice])
  useEffect(() => { if (reMaxPrice == null) setMaxStr('') }, [reMaxPrice])

  const commitMin = useCallback(() => {
    const v = minStr.trim()
    if (v === '') { onReMinPrice(null); return }
    const num = Number(v)
    if (isNaN(num) || num < 0) { setMinStr(reMinPrice != null ? String(reMinPrice) : ''); return }
    const clamped = Math.min(num, 9999)
    setMinStr(String(clamped))
    onReMinPrice(clamped)
  }, [minStr, reMinPrice, onReMinPrice])

  const commitMax = useCallback(() => {
    const v = maxStr.trim()
    if (v === '') { onReMaxPrice(null); return }
    const num = Number(v)
    if (isNaN(num) || num < 0) { setMaxStr(reMaxPrice != null ? String(reMaxPrice) : ''); return }
    const clamped = Math.min(num, 9999)
    setMaxStr(String(clamped))
    onReMaxPrice(clamped)
  }, [maxStr, reMaxPrice, onReMaxPrice])

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
            width: 28, height: 28, flexShrink: 0,
            boxShadow: isFall ? da.logoShadow : '0 0 0 1px rgba(62,123,250,0.3), 0 4px 14px rgba(62,123,250,0.4)',
            borderRadius: 9,
            transition: 'box-shadow 0.3s ease',
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
            border: `1px solid ${C.border}`, borderRadius: 8,
            background: C.surfaceUp, cursor: 'pointer',
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

      {/* 주식 / 부동산 탭 */}
      <div>
        <div style={sectionLabel(C)}>{lang === 'ko' ? '카테고리' : 'Category'}</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, background: C.surfaceAlt, border: `1px solid ${C.borderSub}`, borderRadius: 12, padding: 4 }}>
          {([
            { value: 'stock',       ko: '주식',   en: 'Stock'   },
            { value: 'realestate',  ko: '부동산', en: 'RE'      },
          ] as { value: Tab; ko: string; en: string }[]).map((item) => (
            <button
              key={item.value}
              onClick={() => onTab(item.value)}
              style={{
                width: '100%', textAlign: 'center', padding: '9px 0', border: 'none', borderRadius: 9,
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

          <div>
            <div style={sectionLabel(C)}>Market Cap</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
              {CAP_TIERS.map((c) => (
                <button
                  key={c.value}
                  onClick={() => onCapTier(c.value)}
                  title={c.desc[market][lang]}
                  style={{
                    padding: '7px 4px', borderRadius: 8, border: 'none',
                    fontSize: 12, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', textAlign: 'center',
                    background: capTier === c.value ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
                    color: capTier === c.value ? C.blueSoft : C.textMuted,
                    outline: capTier === c.value ? '1px solid rgba(62,123,250,0.32)' : 'none',
                  }}
                >
                  {c.label[lang]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div style={sectionLabel(C)}>{lang === 'ko' ? '정렬' : 'Sort'}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
              {(['desc', 'asc'] as OrderDir[]).map((o) => {
                const active = stockOrder === o
                const useFall = active && o === 'asc' && isFall
                return (
                  <button
                    key={o}
                    onClick={() => onStockOrder(o)}
                    style={{
                      padding: '7px 4px', borderRadius: 8, border: 'none',
                      fontSize: 11, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', textAlign: 'center',
                      background: active ? (useFall ? da.activeBg : 'rgba(62,123,250,0.14)') : C.surfaceAlt,
                      color: active ? (useFall ? da.activeText : C.blueSoft) : C.textMuted,
                      outline: active ? `1px solid ${useFall ? da.activeBorder : 'rgba(62,123,250,0.32)'}` : 'none',
                    }}
                  >
                    {o === 'desc' ? t.orderRise : t.orderFall}
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}

      {/* ── 부동산 컨트롤 ── */}
      {tab === 'realestate' && (
        <>
          {/* 학군 세그먼트 */}
          {segments.length > 0 && (
            <div>
              <div style={sectionLabel(C)}>{lang === 'ko' ? '학군' : 'School Zone'}</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
                {segments.map((seg) => (
                  <button
                    key={seg.seg_key}
                    onClick={() => onReSeg(reSeg === seg.seg_key ? '' : seg.seg_key)}
                    title={seg.description}
                    style={{
                      padding: '7px 4px', borderRadius: 8, border: 'none',
                      fontSize: 12, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', textAlign: 'center',
                      background: reSeg === seg.seg_key ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
                      color: reSeg === seg.seg_key ? C.blueSoft : C.textMuted,
                      outline: reSeg === seg.seg_key ? '1px solid rgba(62,123,250,0.32)' : 'none',
                    }}
                  >
                    {seg.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 지역 — seg 활성 시 비활성 표시 */}
          <div style={{ opacity: reSeg ? 0.35 : 1, pointerEvents: reSeg ? 'none' : 'auto', transition: 'opacity 0.15s' }}>
            <div style={sectionLabel(C)}>{lang === 'ko' ? '지역' : 'Region'}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
              {RE_REGIONS.map((r) => (
                <button
                  key={r.value}
                  onClick={() => onReRegion(r.value)}
                  style={{
                    padding: '7px 4px', borderRadius: 8, border: 'none',
                    fontSize: 12, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', textAlign: 'center',
                    background: reRegion === r.value && !reGu ? 'rgba(62,123,250,0.14)' : C.surfaceAlt,
                    color: reRegion === r.value && !reGu ? C.blueSoft : C.textMuted,
                    outline: reRegion === r.value && !reGu ? '1px solid rgba(62,123,250,0.32)' : 'none',
                  }}
                >
                  {r.label[lang]}
                </button>
              ))}
            </div>
            {/* 구/동 세부 검색 */}
            <RegionSearch
              lang={lang}
              reGu={reGu}
              reDong={reDong}
              onReGu={onReGu}
            />
          </div>

          {/* 금액 범위 필터 */}
          <div>
            <div style={sectionLabel(C)}>{lang === 'ko' ? '금액 범위' : 'Price Range'}</div>
            <div style={{ fontSize: 10, color: C.textDim, lineHeight: 1.4, marginBottom: 7 }}>
              {lang === 'ko'
                ? '84㎡ 기준 추정가 · 실거래가 아님'
                : '84㎡ estimated · not actual listing'}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <input
                type="number"
                min={0}
                max={9999}
                placeholder={lang === 'ko' ? '최소' : 'min'}
                value={minStr}
                onChange={(e) => setMinStr(e.target.value)}
                onBlur={commitMin}
                onKeyDown={(e) => e.key === 'Enter' && commitMin()}
                style={{
                  flex: 1, minWidth: 0, padding: '7px 8px', borderRadius: 8,
                  border: `1.5px solid ${reMinPrice != null ? 'rgba(62,123,250,0.5)' : C.inputBorder}`,
                  background: C.inputBg, color: C.textPrimary,
                  fontSize: 12, fontFamily: FONT.sans, outline: 'none',
                }}
              />
              <span style={{ color: C.textDim, fontSize: 11, flexShrink: 0 }}>~</span>
              <input
                type="number"
                min={0}
                max={9999}
                placeholder={lang === 'ko' ? '최대' : 'max'}
                value={maxStr}
                onChange={(e) => setMaxStr(e.target.value)}
                onBlur={commitMax}
                onKeyDown={(e) => e.key === 'Enter' && commitMax()}
                style={{
                  flex: 1, minWidth: 0, padding: '7px 8px', borderRadius: 8,
                  border: `1.5px solid ${reMaxPrice != null ? 'rgba(62,123,250,0.5)' : C.inputBorder}`,
                  background: C.inputBg, color: C.textPrimary,
                  fontSize: 12, fontFamily: FONT.sans, outline: 'none',
                }}
              />
              <span style={{ color: C.textDim, fontSize: 11, flexShrink: 0 }}>억</span>
            </div>
            {(reMinPrice != null || reMaxPrice != null) && (
              <button
                onClick={() => { setMinStr(''); setMaxStr(''); onReMinPrice(null); onReMaxPrice(null) }}
                style={{
                  marginTop: 6, width: '100%', padding: '5px 0', borderRadius: 7, border: 'none',
                  fontSize: 11, fontFamily: FONT.sans, cursor: 'pointer',
                  background: C.surfaceAlt, color: C.textDim,
                }}
              >
                {lang === 'ko' ? '금액 필터 초기화' : 'Clear price filter'}
              </button>
            )}
          </div>

          <div>
            <div style={sectionLabel(C)}>Period</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              {RE_PERIODS.map((p, i) => (
                <button
                  key={p.value}
                  onClick={() => onRePeriod(i)}
                  style={{
                    width: '100%', padding: '8px 12px', borderRadius: 9,
                    fontSize: 13, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', textAlign: 'left',
                    background: rePeriodIdx === i ? 'rgba(62,123,250,0.14)' : 'transparent',
                    color: rePeriodIdx === i ? C.blueSoft : C.textDim,
                    border: rePeriodIdx === i ? '1px solid rgba(62,123,250,0.32)' : '1px solid transparent',
                  }}
                >
                  {p.label[lang]}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div style={sectionLabel(C)}>{lang === 'ko' ? '정렬' : 'Sort'}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
              {(['desc', 'asc'] as OrderDir[]).map((o) => {
                const active = reOrder === o
                const useFall = active && o === 'asc' && isFall
                return (
                  <button
                    key={o}
                    onClick={() => onReOrder(o)}
                    style={{
                      padding: '7px 4px', borderRadius: 8, border: 'none',
                      fontSize: 11, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer', textAlign: 'center',
                      background: active ? (useFall ? da.activeBg : 'rgba(62,123,250,0.14)') : C.surfaceAlt,
                      color: active ? (useFall ? da.activeText : C.blueSoft) : C.textMuted,
                      outline: active ? `1px solid ${useFall ? da.activeBorder : 'rgba(62,123,250,0.32)'}` : 'none',
                    }}
                  >
                    {o === 'desc' ? t.orderRise : t.orderFall}
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}

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

      <Footer lang={lang} />
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
