import { useEffect, useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { displayStockName } from '../format'
import { useStockSearch } from '../hooks/useStockSearch'
import { TOSS_UI } from '../i18n/strings.toss'
import type { Market } from '../types'
import { useRouter } from './router'

/**
 * 종목 검색. KOSPI·NASDAQ을 함께 찾아 시장 배지와 함께 보여준다.
 * 상장폐지 종목은 마지막 종가가 과거 날짜라 "종가" 표시와 맞지 않아 숨긴다.
 * 검색어는 URL에 남겨 상세에서 뒤로 돌아왔을 때 그대로 보이게 한다.
 */
export function SearchScreen({ initialQ }: { initialQ: string }) {
  const C = useC()
  const { replace, push } = useRouter()
  const [q, setQ] = useState(initialQ)
  const kospi = useStockSearch('kospi', q)
  const nasdaq = useStockSearch('nasdaq', q)

  useEffect(() => {
    replace({ name: 'search', q })
  }, [q, replace])

  const results = [
    ...kospi.results.map((r) => ({ ...r, market: 'kospi' as Market })),
    ...nasdaq.results.map((r) => ({ ...r, market: 'nasdaq' as Market })),
  ].filter((r) => r.is_active)
  const loading = kospi.loading || nasdaq.loading
  const trimmed = q.trim()

  const message = (title: string, sub?: string) => (
    <div style={{ padding: '48px 24px', textAlign: 'center', fontFamily: FONT.sans }}>
      <div style={{ fontSize: 15, fontWeight: 700, color: C.textSub }}>{title}</div>
      {sub && <div style={{ marginTop: 6, fontSize: 13, color: C.textMuted }}>{sub}</div>}
    </div>
  )

  return (
    <>
      <div style={{ position: 'sticky', top: 0, zIndex: 10, background: C.surface, padding: '12px 16px 10px', borderBottom: `1px solid ${C.borderFaint}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 6px 0 14px', borderRadius: 12, background: C.surfaceAlt }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke={C.textDim} strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
            <circle cx="6.5" cy="6.5" r="4.5" />
            <line x1="10.5" y1="10.5" x2="14" y2="14" />
          </svg>
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value.slice(0, 100))}
            placeholder={TOSS_UI.searchPlaceholder}
            enterKeyHint="search"
            style={{
              flex: 1, minWidth: 0, padding: '12px 0', border: 'none', outline: 'none', background: 'transparent',
              fontSize: 16, color: C.textPrimary, fontFamily: FONT.sans,
            }}
          />
          {q && (
            <button
              onClick={() => setQ('')}
              aria-label="검색어 지우기"
              style={{ width: 40, height: 40, border: 'none', background: 'transparent', color: C.textDim, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                <line x1="4" y1="4" x2="12" y2="12" />
                <line x1="12" y1="4" x2="4" y2="12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {!trimmed && message(TOSS_UI.searchHint)}
      {trimmed && results.length === 0 && (loading ? message(TOSS_UI.searching) : message(TOSS_UI.searchEmpty, TOSS_UI.searchEmptySub))}
      {trimmed && results.map((r) => (
        <div
          key={`${r.market}:${r.ticker}`}
          role="button"
          onClick={() => push({ name: 'stock', market: r.market, ticker: r.ticker })}
          style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', cursor: 'pointer',
            borderBottom: `1px solid ${C.borderFaint}`, fontFamily: FONT.sans,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {r.name ? displayStockName(r.name) : r.ticker}
            </div>
            <div style={{ fontFamily: FONT.mono, fontSize: 11, color: C.textDim, marginTop: 2 }}>{r.ticker}</div>
          </div>
          <span style={{
            flexShrink: 0, fontSize: 11, fontWeight: 700, color: C.blueSoft,
            background: 'rgba(62,123,250,0.12)', padding: '3px 8px', borderRadius: 6,
          }}>
            {r.market.toUpperCase()}
          </span>
        </div>
      ))}
    </>
  )
}
