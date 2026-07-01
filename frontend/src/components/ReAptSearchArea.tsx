import { useState, useRef, useEffect, useCallback } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { RE_PERIODS } from '../types'
import { fetchReAptSearch } from '../api/realestate'
import type { Lang, RealEstatePeriod, ReSearchResultItem } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  period: RealEstatePeriod  // 현재 전역 기간 (초기값으로 사용)
  lang: Lang
  t: Strings
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%'
}

function fmtPrice(v: number | null): string {
  if (v == null) return '—'
  return Math.round(v).toLocaleString('ko-KR') + ' 만원/㎡'
}

function fmtAmount(v: number | null): string {
  if (v == null) return '—'
  const eok = Math.floor(v / 10000)
  const cheon = Math.round((v % 10000) / 1000)
  if (eok > 0 && cheon > 0) return `${eok}억 ${cheon}천만원`
  if (eok > 0) return `${eok}억원`
  return `${v.toLocaleString('ko-KR')}만원`
}

type SearchStatus = 'idle' | 'loading' | 'ok' | 'error'

export function ReAptSearchArea({ period: globalPeriod, lang, t }: Props) {
  const C = useC()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [localPeriodIdx, setLocalPeriodIdx] = useState(
    () => Math.max(0, RE_PERIODS.findIndex((p) => p.value === globalPeriod))
  )
  const [results, setResults] = useState<ReSearchResultItem[]>([])
  const [searchStatus, setSearchStatus] = useState<SearchStatus>('idle')
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [selectedItem, setSelectedItem] = useState<ReSearchResultItem | null>(null)
  const [selectedAptName, setSelectedAptName] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const detailTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 전역 기간이 변경되면 로컬 기간도 동기화 (단, 사용자가 변경했으면 유지)
  useEffect(() => {
    const idx = RE_PERIODS.findIndex((p) => p.value === globalPeriod)
    if (idx >= 0) setLocalPeriodIdx(idx)
  }, [globalPeriod])

  const localPeriod = RE_PERIODS[localPeriodIdx]!.value

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // 검색 — 드롭다운이 열려 있고 q가 있을 때
  useEffect(() => {
    if (!open || !q.trim()) {
      setResults([])
      setSearchStatus('idle')
      return
    }

    setSearchStatus('loading')
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)

    searchTimerRef.current = setTimeout(() => {
      fetchReAptSearch(q, localPeriod)
        .then((data) => {
          setResults(data.results)
          setSearchStatus('ok')
        })
        .catch(() => {
          setResults([])
          setSearchStatus('error')
        })
    }, 300)

    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    }
  }, [open, q, localPeriod])

  // 선택된 apt 데이터 갱신 — 기간 변경 시
  useEffect(() => {
    if (!selectedKey || !selectedAptName) return

    setSelectedItem(null)
    if (detailTimerRef.current) clearTimeout(detailTimerRef.current)

    detailTimerRef.current = setTimeout(() => {
      fetchReAptSearch(selectedAptName, localPeriod)
        .then((data) => {
          const found = data.results.find((r) => r.complex_key === selectedKey)
          setSelectedItem(found ?? null)
        })
        .catch(() => setSelectedItem(null))
    }, 300)

    return () => {
      if (detailTimerRef.current) clearTimeout(detailTimerRef.current)
    }
  }, [selectedKey, selectedAptName, localPeriod])

  const handleSelect = useCallback((item: ReSearchResultItem) => {
    setSelectedKey(item.complex_key)
    setSelectedAptName(item.apt_name)
    setSelectedItem(item)
    setQ(item.display_name ?? item.apt_name)
    setOpen(false)
  }, [])

  const handleClear = useCallback(() => {
    setQ('')
    setSelectedKey(null)
    setSelectedItem(null)
    setSelectedAptName(null)
    setOpen(false)
    setResults([])
  }, [])

  const statusTag = (status: ReSearchResultItem['data_status']) => {
    if (status === 'ok') return null
    const labels: Record<string, string> = {
      no_snapshot: lang === 'ko' ? '데이터 없음' : 'No data',
      insufficient: lang === 'ko' ? '데이터 부족' : 'Insufficient',
      no_start: lang === 'ko' ? '시작 데이터 없음' : 'No start',
      no_end: lang === 'ko' ? '종료 데이터 없음' : 'No end',
    }
    return labels[status] ?? status
  }

  return (
    <div ref={containerRef} style={{ fontFamily: FONT.sans, background: C.surface }}>
      {/* ── 섹션 헤더 + 검색 입력 ───────────────────────────────────────── */}
      <div style={{
        padding: '14px 16px 10px',
        borderBottom: selectedKey ? 'none' : `1px solid ${C.borderSub}`,
        position: 'relative',
      }}>
        <div style={{
          fontSize: 10, fontWeight: 700, color: C.textDim,
          letterSpacing: '0.08em', textTransform: 'uppercase',
          marginBottom: 8,
        }}>
          {lang === 'ko' ? '아파트 검색' : 'Apt Search'}
        </div>

        <div style={{
          display: 'flex', alignItems: 'center', gap: 9,
          background: C.surfaceAlt,
          border: `1.5px solid ${open ? 'rgba(62,123,250,0.55)' : 'rgba(62,123,250,0.22)'}`,
          borderRadius: 10, padding: '9px 13px',
          transition: 'border-color 0.15s',
        }}>
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke={C.blueSoft} strokeWidth="1.8" strokeLinecap="round">
            <circle cx="6.5" cy="6.5" r="4.5" />
            <line x1="10.5" y1="10.5" x2="14" y2="14" />
          </svg>
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setOpen(true)
              if (!e.target.value) {
                setSelectedKey(null)
                setSelectedItem(null)
                setSelectedAptName(null)
              }
            }}
            onFocus={() => { if (q && !selectedKey) setOpen(true) }}
            placeholder={lang === 'ko' ? '아파트명 검색 (예: 래미안, 자이)' : 'Search apt name (e.g. Raemian)'}
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
                cursor: 'pointer', color: C.textMuted,
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
            background: C.surface,
            border: '1.5px solid rgba(62,123,250,0.28)',
            borderRadius: 10, boxShadow: '0 8px 28px rgba(0,0,0,0.28)',
            zIndex: 50, overflow: 'hidden', maxHeight: 260, overflowY: 'auto',
          }}>
            {searchStatus === 'loading' && (
              <div style={{ padding: '12px 14px', fontSize: 12, color: C.textDim }}>
                {lang === 'ko' ? '검색 중…' : 'Searching…'}
              </div>
            )}
            {searchStatus === 'ok' && results.length === 0 && (
              <div style={{ padding: '12px 14px', fontSize: 12, color: C.textDim }}>
                {lang === 'ko' ? '결과 없음' : 'No results'}
              </div>
            )}
            {results.map((r) => {
              const tag = statusTag(r.data_status)
              const location = r.sigungu_name
                ? `${r.sigungu_name} ${r.eupmyeondong}`
                : r.eupmyeondong
              return (
                <div
                  key={r.complex_key}
                  onMouseDown={(e) => { e.preventDefault(); handleSelect(r) }}
                  style={{
                    padding: '9px 14px', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 10,
                    borderBottom: `1px solid ${C.borderFaint}`,
                    background: selectedKey === r.complex_key ? C.surfaceAlt : 'transparent',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.background = C.hoverBg }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLDivElement).style.background =
                      selectedKey === r.complex_key ? C.surfaceAlt : 'transparent'
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 13, color: C.textPrimary,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {r.apt_name}
                    </div>
                    <div style={{ fontSize: 11, color: C.textDim, marginTop: 1 }}>
                      {location}
                    </div>
                  </div>
                  {r.data_status === 'ok' && r.change_pct != null && (
                    <span style={{
                      fontFamily: FONT.mono, fontSize: 12, fontWeight: 700,
                      color: r.change_pct >= 0 ? C.green : C.red,
                      flexShrink: 0,
                    }}>
                      {fmtPct(r.change_pct)}
                    </span>
                  )}
                  {tag && (
                    <span style={{
                      fontSize: 10, color: C.textDim,
                      background: C.surfaceAlt, padding: '2px 6px', borderRadius: 4,
                      flexShrink: 0,
                    }}>
                      {tag}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ── 선택된 아파트 데이터 패널 ─────────────────────────────────────── */}
      {selectedKey && (
        <div style={{
          margin: '0 12px 12px',
          background: C.surfaceBt,
          border: `1px solid ${C.borderSub}`,
          borderLeft: `3px solid ${C.blue}`,
          borderRadius: '0 0 10px 10px',
          borderTop: 'none',
          padding: '12px 14px 14px',
        }}>
          {/* 아파트 헤더 */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary, lineHeight: 1.3 }}>
              {selectedItem?.display_name ?? selectedItem?.apt_name ?? selectedAptName}
            </div>
            {selectedItem?.sigungu_name && (
              <div style={{ fontSize: 11, color: C.textDim, marginTop: 2 }}>
                {selectedItem.sigungu_name} {selectedItem.eupmyeondong}
              </div>
            )}
          </div>

          {/* 기간 탭 */}
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 10 }}>
            {RE_PERIODS.map((p, i) => {
              const active = localPeriodIdx === i
              return (
                <button
                  key={p.value}
                  onClick={() => setLocalPeriodIdx(i)}
                  style={{
                    padding: '5px 10px', borderRadius: 7, fontSize: 11.5, fontWeight: 600,
                    fontFamily: FONT.sans, cursor: 'pointer',
                    background: active ? 'rgba(62,123,250,0.15)' : C.surfaceAlt,
                    color: active ? C.blueSoft : C.textMuted,
                    border: active ? '1px solid rgba(62,123,250,0.35)' : `1px solid ${C.borderSub}`,
                  }}
                >
                  {p.label[lang]}
                </button>
              )
            })}
          </div>

          {/* 데이터 상태별 표시 */}
          {selectedItem == null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 0' }}>
              <div style={{
                width: 14, height: 14, borderRadius: '50%',
                border: '2px solid rgba(62,123,250,0.25)', borderTopColor: C.blue,
                animation: 'fb-spin .8s linear infinite',
              }} />
              <span style={{ fontSize: 12, color: C.textDim }}>{t.btLoading}</span>
            </div>
          )}

          {selectedItem?.data_status === 'no_snapshot' && (
            <div style={{
              padding: '10px 12px', borderRadius: 8,
              background: C.surfaceAlt, border: `1px solid ${C.borderSub}`,
              fontSize: 12, color: C.textDim, lineHeight: 1.5,
            }}>
              {lang === 'ko'
                ? `이 아파트의 ${RE_PERIODS[localPeriodIdx]!.label.ko} 데이터가 없습니다. 다른 기간을 선택해보세요.`
                : `No ${RE_PERIODS[localPeriodIdx]!.label.en} data for this apartment. Try another period.`}
            </div>
          )}

          {selectedItem != null && selectedItem.data_status !== 'ok' && selectedItem.data_status !== 'no_snapshot' && (
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: 7,
              padding: '9px 11px', borderRadius: 8,
              background: C.orangeFill, border: '1px solid rgba(244,169,60,0.22)',
              fontSize: 11.5, color: '#B8924E', lineHeight: 1.45,
            }}>
              <span style={{ color: C.orange, flexShrink: 0, marginTop: 1 }}>⚠</span>
              <span>
                {selectedItem.insufficient_reason
                  ?? (lang === 'ko' ? '거래 데이터가 부족합니다.' : 'Insufficient transaction data.')}
              </span>
            </div>
          )}

          {selectedItem?.data_status === 'ok' && (() => {
            const d = selectedItem
            const retColor = d.change_pct == null ? C.textDim : d.change_pct >= 0 ? C.green : C.red
            const ymRange = d.start_ym && d.end_ym
              ? `${d.start_ym.slice(0, 4)}.${d.start_ym.slice(4)} ~ ${d.end_ym.slice(0, 4)}.${d.end_ym.slice(4)}`
              : null

            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* 상승률 */}
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
                  <div>
                    <div style={{ fontSize: 10, color: C.textDim, marginBottom: 3, letterSpacing: '0.04em' }}>
                      {lang === 'ko' ? '기간 상승률' : 'Period Return'}
                    </div>
                    <div style={{
                      fontFamily: FONT.mono, fontSize: 28, fontWeight: 800,
                      color: retColor, letterSpacing: '-0.02em', lineHeight: 1,
                    }}>
                      {fmtPct(d.change_pct)}
                    </div>
                  </div>
                  {d.rank != null && (
                    <div style={{ paddingBottom: 3 }}>
                      <div style={{ fontSize: 10, color: C.textDim, marginBottom: 2 }}>
                        {lang === 'ko' ? '순위' : 'Rank'}
                      </div>
                      <div style={{ fontFamily: FONT.mono, fontSize: 14, fontWeight: 700, color: C.textSub }}>
                        #{d.rank}
                      </div>
                    </div>
                  )}
                </div>

                {/* 평단가 변화 */}
                {(d.start_price != null || d.end_price != null) && (
                  <div>
                    <div style={{ fontSize: 10, color: C.textDim, marginBottom: 4 }}>
                      {lang === 'ko' ? '㎡당 중위 단가' : 'Median price/㎡'}
                    </div>
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      fontSize: 12, fontFamily: FONT.mono, color: C.textMuted,
                    }}>
                      <span>{fmtPrice(d.start_price)}</span>
                      <span style={{ color: C.textDim }}>→</span>
                      <span style={{ color: retColor, fontWeight: 600 }}>
                        {fmtPrice(d.end_price)}
                      </span>
                    </div>
                  </div>
                )}

                {/* 거래금액 변화 */}
                {(d.start_deal_amount != null || d.end_deal_amount != null) && (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
                      <span style={{ fontSize: 10, color: C.textDim }}>
                        {lang === 'ko' ? '추정 거래금액' : 'Est. deal price'}
                      </span>
                      <span style={{
                        fontSize: 9, color: C.textDim,
                        background: C.surfaceAlt, border: `1px solid ${C.borderSub}`,
                        padding: '1px 5px', borderRadius: 4,
                      }}>
                        {lang === 'ko' ? '국평기준' : '84㎡'}
                      </span>
                    </div>
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      fontSize: 12, fontFamily: FONT.mono, color: C.textMuted,
                    }}>
                      <span>{fmtAmount(d.start_deal_amount)}</span>
                      <span style={{ color: C.textDim }}>→</span>
                      <span style={{ color: retColor, fontWeight: 600 }}>
                        {fmtAmount(d.end_deal_amount)}
                      </span>
                    </div>
                  </div>
                )}

                {/* 기간 */}
                {ymRange && (
                  <div style={{ fontSize: 10.5, color: C.textDim, fontFamily: FONT.mono }}>
                    {ymRange}
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      )}

      {selectedKey && (
        <div style={{ height: 1, background: C.borderSub }} />
      )}
    </div>
  )
}
