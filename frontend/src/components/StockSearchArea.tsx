import { useState, useRef, useEffect, useCallback } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { PERIODS } from '../types'
import { useStockSearch } from '../hooks/useStockSearch'
import { useStockQuote } from '../hooks/useStockQuote'
import type { Market, Lang, Period } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  market: Market
  lang: Lang
  t: Strings
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%'
}

function fmtPrice(v: number | null, market: Market): string {
  if (v == null) return '—'
  if (market === 'kospi') return '₩' + Math.round(v).toLocaleString('ko-KR')
  return '$' + v.toFixed(2)
}

export function StockSearchArea({ market, lang, t }: Props) {
  const C = useC()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [ticker, setTicker] = useState<string | null>(null)
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [fixedPeriodIdx, setFixedPeriodIdx] = useState(2) // 30d
  const [customMode, setCustomMode] = useState(false)
  const [startInput, setStartInput] = useState('')
  const [endInput, setEndInput] = useState('')
  const [applied, setApplied] = useState<{ start: string; end: string } | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const { results, loading: searching } = useStockSearch(market, open ? q : '')

  const period: Period | null = customMode ? null : (PERIODS[fixedPeriodIdx]!.value as Period)
  const quoteState = useStockQuote(
    market,
    ticker,
    period,
    applied?.start,
    applied?.end,
  )

  // market 바뀌면 초기화
  useEffect(() => {
    setQ('')
    setTicker(null)
    setSelectedName(null)
    setOpen(false)
    setApplied(null)
    setCustomMode(false)
  }, [market])

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSelect = useCallback((tk: string, name: string | null) => {
    setTicker(tk)
    setSelectedName(name)
    setQ(name ?? tk)
    setOpen(false)
    setApplied(null)
    setCustomMode(false)
    setFixedPeriodIdx(2)
  }, [])

  const handleClear = useCallback(() => {
    setQ('')
    setTicker(null)
    setSelectedName(null)
    setOpen(false)
    setApplied(null)
    setCustomMode(false)
  }, [])

  const handleApplyCustom = useCallback(() => {
    if (startInput && endInput && startInput <= endInput) {
      setApplied({ start: startInput, end: endInput })
    }
  }, [startInput, endInput])

  const isCustomValid = !!startInput && !!endInput && startInput <= endInput

  return (
    <div
      ref={containerRef}
      style={{
        borderBottom: `1px solid ${C.borderSub}`,
        fontFamily: FONT.sans,
        background: C.surface,
      }}
    >
      {/* 검색 입력 */}
      <div style={{ padding: '12px 16px 10px', position: 'relative' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: C.surfaceAlt,
          border: `1px solid ${open ? 'rgba(62,123,250,0.4)' : C.border}`,
          borderRadius: 10, padding: '8px 12px',
          transition: 'border-color 0.15s',
        }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke={C.textDim} strokeWidth="1.8" strokeLinecap="round">
            <circle cx="6.5" cy="6.5" r="4.5" />
            <line x1="10.5" y1="10.5" x2="14" y2="14" />
          </svg>
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setOpen(true)
              if (!e.target.value) {
                setTicker(null)
                setSelectedName(null)
              }
            }}
            onFocus={() => { if (q) setOpen(true) }}
            placeholder={lang === 'ko' ? '종목명 또는 코드 검색' : 'Search ticker or name'}
            style={{
              flex: 1, border: 'none', outline: 'none',
              background: 'transparent', fontSize: 13,
              color: C.textPrimary, fontFamily: FONT.sans,
            }}
          />
          {q && (
            <button
              onClick={handleClear}
              style={{
                border: 'none', background: 'transparent',
                cursor: 'pointer', color: C.textDim,
                fontSize: 13, padding: 0, lineHeight: 1,
                display: 'flex', alignItems: 'center',
              }}
            >
              ✕
            </button>
          )}
        </div>

        {/* 드롭다운 */}
        {open && q.length > 0 && (
          <div style={{
            position: 'absolute', left: 16, right: 16, top: 'calc(100% - 4px)',
            background: C.surface, border: `1px solid ${C.border}`,
            borderRadius: 10, boxShadow: '0 8px 28px rgba(0,0,0,0.22)',
            zIndex: 50, overflow: 'hidden', maxHeight: 220, overflowY: 'auto',
          }}>
            {searching && (
              <div style={{ padding: '12px 14px', fontSize: 12, color: C.textDim }}>
                {lang === 'ko' ? '검색 중…' : 'Searching…'}
              </div>
            )}
            {!searching && results.length === 0 && (
              <div style={{ padding: '12px 14px', fontSize: 12, color: C.textDim }}>
                {lang === 'ko' ? '결과 없음' : 'No results'}
              </div>
            )}
            {results.map((r) => (
              <div
                key={r.ticker}
                onMouseDown={(e) => { e.preventDefault(); handleSelect(r.ticker, r.name) }}
                style={{
                  padding: '9px 14px', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 10,
                  borderBottom: `1px solid ${C.borderFaint}`,
                  background: ticker === r.ticker ? C.surfaceAlt : 'transparent',
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = C.hoverBg }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = ticker === r.ticker ? C.surfaceAlt : 'transparent' }}
              >
                <span style={{
                  fontFamily: FONT.mono, fontSize: 11, color: C.blueSoft,
                  background: 'rgba(62,123,250,0.12)', padding: '2px 7px', borderRadius: 5,
                  flexShrink: 0,
                }}>
                  {r.ticker}
                </span>
                <span style={{ fontSize: 13, color: C.textPrimary, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.name ?? r.ticker}
                </span>
                {!r.is_active && (
                  <span style={{
                    fontSize: 10, color: C.textDim,
                    background: C.surfaceAlt, padding: '1px 5px', borderRadius: 4, flexShrink: 0,
                  }}>
                    {lang === 'ko' ? '상장폐지' : 'Delisted'}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quote 패널 */}
      {ticker && (
        <div style={{ padding: '0 16px 14px' }}>
          {/* 종목 헤더 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary }}>
              {selectedName ?? ticker}
            </span>
            {selectedName && (
              <span style={{ fontSize: 11, color: C.textDim, fontFamily: FONT.mono }}>{ticker}</span>
            )}
          </div>

          {/* 기간 탭 */}
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 10 }}>
            {PERIODS.map((p, i) => {
              const active = !customMode && fixedPeriodIdx === i
              return (
                <button
                  key={p.value}
                  onClick={() => { setFixedPeriodIdx(i); setCustomMode(false); setApplied(null) }}
                  style={{
                    padding: '5px 10px', borderRadius: 7, fontSize: 11.5, fontWeight: 600,
                    fontFamily: FONT.sans, cursor: 'pointer',
                    background: active ? 'rgba(62,123,250,0.14)' : 'transparent',
                    color: active ? C.blueSoft : C.textDim,
                    border: active ? '1px solid rgba(62,123,250,0.32)' : '1px solid transparent',
                  }}
                >
                  {p.label[lang]}
                </button>
              )
            })}
            <button
              onClick={() => setCustomMode((v) => !v)}
              style={{
                padding: '5px 10px', borderRadius: 7, fontSize: 11.5, fontWeight: 600,
                fontFamily: FONT.sans, cursor: 'pointer',
                background: customMode ? 'rgba(62,123,250,0.14)' : 'transparent',
                color: customMode ? C.blueSoft : C.textDim,
                border: customMode ? '1px solid rgba(62,123,250,0.32)' : '1px solid transparent',
              }}
            >
              {lang === 'ko' ? '직접 입력' : 'Custom'}
            </button>
          </div>

          {/* 커스텀 날짜 입력 */}
          {customMode && (
            <div style={{
              display: 'flex', gap: 6, alignItems: 'center',
              flexWrap: 'wrap', marginBottom: 10,
            }}>
              <input
                type="date"
                value={startInput}
                onChange={(e) => setStartInput(e.target.value)}
                style={{
                  padding: '5px 8px', borderRadius: 7, fontSize: 12,
                  border: `1px solid ${C.border}`, background: C.surfaceAlt,
                  color: C.textPrimary, fontFamily: FONT.sans,
                }}
              />
              <span style={{ fontSize: 12, color: C.textDim }}>~</span>
              <input
                type="date"
                value={endInput}
                onChange={(e) => setEndInput(e.target.value)}
                style={{
                  padding: '5px 8px', borderRadius: 7, fontSize: 12,
                  border: `1px solid ${C.border}`, background: C.surfaceAlt,
                  color: C.textPrimary, fontFamily: FONT.sans,
                }}
              />
              <button
                onClick={handleApplyCustom}
                disabled={!isCustomValid}
                style={{
                  padding: '5px 14px', borderRadius: 7, fontSize: 12, fontWeight: 600,
                  fontFamily: FONT.sans, cursor: isCustomValid ? 'pointer' : 'default',
                  background: 'rgba(62,123,250,0.14)', color: C.blueSoft,
                  border: '1px solid rgba(62,123,250,0.32)',
                  opacity: isCustomValid ? 1 : 0.45,
                }}
              >
                {lang === 'ko' ? '조회' : 'Query'}
              </button>
            </div>
          )}

          {/* Quote 데이터 */}
          {quoteState.status === 'loading' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 0' }}>
              <div style={{
                width: 14, height: 14, borderRadius: '50%',
                border: '2px solid rgba(62,123,250,0.25)', borderTopColor: C.blue,
                animation: 'fb-spin .8s linear infinite',
              }} />
              <span style={{ fontSize: 12, color: C.textDim }}>{t.btLoading}</span>
            </div>
          )}

          {quoteState.status === 'error' && (
            <div style={{ fontSize: 12, color: C.textDim, padding: '8px 0' }}>
              {lang === 'ko' ? '데이터를 불러오지 못했어요' : 'Failed to load data'}
            </div>
          )}

          {quoteState.status === 'ok' && (() => {
            const d = quoteState.data
            const ret = d.return_pct
            const retColor = ret == null ? C.textDim : ret >= 0 ? C.green : C.red
            const dateRange = d.start_date && d.end_date
              ? `${d.start_date} ~ ${d.end_date}`
              : null

            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                {/* 수익률 + 보조 지표 */}
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 18, flexWrap: 'wrap' }}>
                  <div>
                    <div style={{ fontSize: 10, color: C.textDim, marginBottom: 3 }}>
                      {lang === 'ko' ? '기간 수익률' : 'Period Return'}
                    </div>
                    <div style={{
                      fontFamily: FONT.mono, fontSize: 30, fontWeight: 800,
                      color: retColor, letterSpacing: '-0.02em', lineHeight: 1,
                    }}>
                      {fmtPct(ret)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 14, paddingBottom: 3 }}>
                    {d.mdd_pct != null && (
                      <div>
                        <div style={{ fontSize: 10, color: C.textDim, marginBottom: 2 }}>MDD</div>
                        <div style={{ fontFamily: FONT.mono, fontSize: 13, fontWeight: 700, color: C.red }}>
                          {fmtPct(d.mdd_pct)}
                        </div>
                      </div>
                    )}
                    {d.volatility_annualized_pct != null && (
                      <div>
                        <div style={{ fontSize: 10, color: C.textDim, marginBottom: 2 }}>{t.volatilityLabel}</div>
                        <div style={{ fontFamily: FONT.mono, fontSize: 13, fontWeight: 700, color: C.textSub }}>
                          {fmtPct(d.volatility_annualized_pct)}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* 시작가 → 종료가 */}
                {d.start_price != null && d.end_price != null && (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    fontSize: 12, fontFamily: FONT.mono, color: C.textMuted,
                  }}>
                    <span>{fmtPrice(d.start_price, market)}</span>
                    <span style={{ color: C.textDim }}>→</span>
                    <span style={{ color: retColor, fontWeight: 600 }}>{fmtPrice(d.end_price, market)}</span>
                    {dateRange && (
                      <span style={{ fontSize: 10, color: C.textDim, marginLeft: 4 }}>{dateRange}</span>
                    )}
                  </div>
                )}

                {/* 데이터 커버리지 경고 */}
                {d.data_coverage.warning && (
                  <div style={{
                    display: 'flex', alignItems: 'flex-start', gap: 7,
                    padding: '8px 10px', borderRadius: 8,
                    background: C.orangeFill, border: '1px solid rgba(244,169,60,0.16)',
                    fontSize: 11, color: '#B8924E', lineHeight: 1.4,
                  }}>
                    <span style={{ color: C.orange, flexShrink: 0 }}>⚠</span>
                    <span>{d.data_coverage.warning}</span>
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
