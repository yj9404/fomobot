import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import type { ReRankingItem, ReRankingsMeta, Lang } from '../types'

interface Props {
  rankings: ReRankingItem[]
  excluded: ReRankingItem[]
  meta: ReRankingsMeta | null
  lang: Lang
}

function fmtPct(n: number | null): string {
  if (n == null) return '—'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

const DATA_STATUS_LABEL: Record<string, Record<Lang, string>> = {
  insufficient: { ko: '거래량 부족', en: 'Insufficient trades' },
  no_start:     { ko: '시작 시점 데이터 없음', en: 'No start data' },
  no_end:       { ko: '종료 시점 데이터 없음', en: 'No end data' },
}

// 갈아끼우기용 결과 컴포넌트 — 이번엔 단순 목록 플레이스홀더
export function ReResultArea({ rankings, excluded, meta, lang }: Props) {
  const C = useC()

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
        {rankings.map((item) => (
          <div
            key={`${item.sigungu_code}-${item.eupmyeondong ?? ''}`}
            style={{
              padding: '14px 20px',
              borderBottom: `1px solid ${C.borderFaint}`,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
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
                {item.start_ym} → {item.end_ym}
              </div>
            </div>

            <span style={{
              fontFamily: FONT.mono, fontSize: 17, fontWeight: 800,
              color: item.change_pct != null && item.change_pct >= 0 ? C.green : C.red,
              flexShrink: 0,
            }}>
              {fmtPct(item.change_pct)}
            </span>
          </div>
        ))}
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
                key={`${item.sigungu_code}-${item.eupmyeondong ?? ''}`}
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
