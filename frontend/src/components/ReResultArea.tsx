import { useState, useEffect } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import type { ReRankingItem, ReRankingsMeta, Lang, RealEstatePeriod } from '../types'

interface Props {
  rankings: ReRankingItem[]
  excluded: ReRankingItem[]
  meta: ReRankingsMeta | null
  lang: Lang
  period: RealEstatePeriod
}

function fmtPct(n: number | null): string {
  if (n == null) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}


function fmtWon(manwon: number | null): string {
  if (manwon == null) return '—'
  const eok = Math.floor(manwon / 10000)
  const remainder = Math.round(manwon % 10000)
  const cheon = Math.floor(remainder / 1000)
  if (eok > 0 && cheon > 0) return `${eok}억 ${cheon}천`
  if (eok > 0) return `${eok}억`
  if (cheon > 0) return `${cheon}천만`
  return `${remainder}만`
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

const DATA_STATUS_LABEL: Record<string, Record<Lang, string>> = {
  insufficient: { ko: '거래량 부족', en: 'Insufficient trades' },
  no_start:     { ko: '시작 시점 데이터 없음', en: 'No start data' },
  no_end:       { ko: '종료 시점 데이터 없음', en: 'No end data' },
}

export function ReResultArea({ rankings, excluded, meta, lang, period }: Props) {
  const C = useC()
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [detailItem, setDetailItem] = useState<ReRankingItem | null>(null)

  // 기간·필터 변경 시 선택 초기화
  useEffect(() => {
    setSelectedKey(null)
    setDetailItem(null)
  }, [period])

  const handleRowClick = (item: ReRankingItem) => {
    if (selectedKey === item.complex_key) {
      setSelectedKey(null)
      setDetailItem(null)
    } else {
      setSelectedKey(item.complex_key)
      setDetailItem(item)
    }
  }

  const renderDetail = (item: ReRankingItem) => {
    const retColor = item.change_pct == null ? C.textDim : item.change_pct >= 0 ? C.green : C.red
    const ymRange = item.start_ym && item.end_ym
      ? `${item.start_ym.slice(0, 4)}.${item.start_ym.slice(4)} ~ ${item.end_ym.slice(0, 4)}.${item.end_ym.slice(4)}`
      : null

    return (
      <div style={{
        background: C.surfaceBt,
        borderTop: `1px solid ${C.borderFaint}`,
        padding: '12px 14px 14px 20px',
      }}>
        {item.data_status !== 'ok' && (
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: 7,
            padding: '9px 11px', borderRadius: 8,
            background: C.orangeFill, border: '1px solid rgba(244,169,60,0.22)',
            fontSize: 11.5, color: '#B8924E', lineHeight: 1.45,
          }}>
            <span style={{ color: C.orange, flexShrink: 0, marginTop: 1 }}>⚠</span>
            <span>
              {item.insufficient_reason
                ?? (lang === 'ko' ? '거래 데이터가 부족합니다.' : 'Insufficient transaction data.')}
            </span>
          </div>
        )}

        {item.data_status === 'ok' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* 평단가 변화 */}
            {(item.start_price != null || item.end_price != null) && (
              <div>
                <div style={{ fontSize: 10, color: C.textDim, marginBottom: 4 }}>
                  {lang === 'ko' ? '㎡당 중위 단가' : 'Median price/㎡'}
                </div>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 12, fontFamily: FONT.mono, color: C.textMuted,
                }}>
                  <span>{fmtPrice(item.start_price)}</span>
                  <span style={{ color: C.textDim }}>→</span>
                  <span style={{ color: retColor, fontWeight: 600 }}>
                    {fmtPrice(item.end_price)}
                  </span>
                </div>
              </div>
            )}

            {/* 거래금액 변화 — 국평(84㎡) 기준 추정 */}
            {(item.start_price != null || item.end_price != null) && (
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
                    84㎡ 가정
                  </span>
                </div>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  fontSize: 12, fontFamily: FONT.mono, color: C.textMuted,
                }}>
                  <span>{fmtAmount(item.start_price != null ? item.start_price * 84 : null)}</span>
                  <span style={{ color: C.textDim }}>→</span>
                  <span style={{ color: retColor, fontWeight: 600 }}>
                    {fmtAmount(item.end_price != null ? item.end_price * 84 : null)}
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
        )}
      </div>
    )
  }

  return (
    <div style={{ fontFamily: FONT.sans }}>
      {/* 메타 정보 */}
      {meta && (
        <div style={{
          padding: '12px 20px',
          borderBottom: `1px solid ${C.borderSub}`,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 11, color: C.textDim, fontFamily: FONT.mono }}>
            {lang === 'ko' ? '기준월' : 'as of'} {meta.snapshot_ym}
          </span>
          <span style={{ fontSize: 11, color: C.textDim }}>·</span>
          <span style={{ fontSize: 11, color: C.textDim }}>
            {meta.total_complexes}{lang === 'ko' ? '개 단지' : ' complexes'}
          </span>
          {meta.is_recent_incomplete && (
            <span style={{
              fontSize: 10, color: C.orange,
              background: C.orangeFill, border: `1px solid rgba(244,169,60,0.2)`,
              padding: '2px 8px', borderRadius: 6,
            }}>
              {lang === 'ko' ? '⚠ 최근 데이터 미확정' : '⚠ Recent data may be incomplete'}
            </span>
          )}
        </div>
      )}

      {/* 랭킹 목록 */}
      <div>
        {rankings.map((item) => {
          const isSelected = selectedKey === item.complex_key
          return (
            <div
              key={item.complex_key}
              style={{
                borderLeft: isSelected ? `3px solid ${C.blue}` : '3px solid transparent',
                borderBottom: `1px solid ${isSelected ? C.borderSub : C.borderFaint}`,
                transition: 'border-color 0.12s',
              }}
            >
              <div
                onClick={() => handleRowClick(item)}
                style={{
                  padding: '14px 17px 14px 17px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  cursor: 'pointer',
                  background: isSelected ? C.surfaceAlt : 'transparent',
                  transition: 'background 0.12s',
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLDivElement).style.background = C.hoverBg
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLDivElement).style.background = 'transparent'
                }}
              >
                <span style={{
                  fontFamily: FONT.mono, fontSize: 12, fontWeight: 700, color: C.blueSoft,
                  background: 'rgba(62,123,250,0.12)', width: 28, height: 28, borderRadius: 8,
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  {String(item.rank ?? 0).padStart(2, '0')}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14.5, fontWeight: 700, color: C.textPrimary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.display_name}
                  </div>
                  <div style={{ fontSize: 11, color: C.textDim, marginTop: 2, fontFamily: FONT.mono }}>
                    {fmtWon(item.start_price != null ? item.start_price * 84 : null)} → {fmtWon(item.end_price != null ? item.end_price * 84 : null)}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                  <span style={{
                    fontFamily: FONT.mono, fontSize: 17, fontWeight: 800,
                    color: item.change_pct != null && item.change_pct >= 0 ? C.green : C.red,
                  }}>
                    {fmtPct(item.change_pct)}
                  </span>
                  <span style={{
                    fontSize: 12, color: isSelected ? C.blueSoft : C.textDim,
                    transition: 'transform 0.15s',
                    display: 'inline-block',
                    transform: isSelected ? 'rotate(180deg)' : 'rotate(0deg)',
                  }}>
                    ▾
                  </span>
                </div>
              </div>

              {/* 인라인 상세 패널 */}
              {isSelected && detailItem && renderDetail(detailItem)}
            </div>
          )
        })}
      </div>

      {/* 데이터 부족 지역 */}
      {excluded.length > 0 && (
        <div style={{
          margin: '16px 20px',
          padding: '10px 14px',
          background: C.orangeFill,
          border: `1px solid rgba(244,169,60,0.16)`,
          borderRadius: 10,
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: C.orange, marginBottom: 6 }}>
            {lang === 'ko'
              ? `${excluded.length}개 지역 제외 (데이터 부족)`
              : `${excluded.length} regions excluded (insufficient data)`}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px 10px' }}>
            {excluded.map((item) => (
              <span
                key={item.complex_key}
                style={{ fontSize: 11, color: C.textDim }}
                title={DATA_STATUS_LABEL[item.data_status]?.[lang] ?? item.data_status}
              >
                {item.display_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {rankings.length > 0 && (
        <div style={{ textAlign: 'center', fontSize: 11, color: C.textDim, fontFamily: FONT.mono, padding: '12px 0 20px' }}>
          Top {rankings.length} · {lang === 'ko' ? '㎡당 평단가 중위값 기준' : 'median price per ㎡'}
        </div>
      )}
    </div>
  )
}
