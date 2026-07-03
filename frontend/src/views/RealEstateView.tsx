import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { SkeletonList } from '../components/SkeletonList'
import { ErrorState } from '../components/ErrorState'
import { ReResultArea } from '../components/ReResultArea'
import { ReAptSearchArea } from '../components/ReAptSearchArea'
import { useRealEstateRankings } from '../hooks/useRealEstateRankings'
import type { Lang, RealEstatePeriod } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  lang: Lang
  period: RealEstatePeriod
  sido: string          // 시도 필터 ('11'=서울 등, ''=수도권 전체)
  gu?: string           // 5자리 시군구 코드 (sido보다 좁은 필터)
  dong?: string         // 법정동명 부분일치
  seg?: string          // 학군 세그먼트 키 (지정 시 sido/gu/dong 무시)
  minPrice?: number | null   // 84㎡ 환산 금액 하한 (억 단위)
  maxPrice?: number | null   // 84㎡ 환산 금액 상한 (억 단위)
  retryKey: number
  onRetry: () => void
  onResetFilters: () => void
  t: Strings
}

export function RealEstateView({ lang, period, sido, gu, dong, seg, minPrice, maxPrice, retryKey, onRetry, onResetFilters, t }: Props) {
  const { status, rankings, excluded, meta } = useRealEstateRankings(period, sido, retryKey, gu, dong, seg, minPrice, maxPrice)
  const C = useC()

  if (status === 'loading') return (
    <>
      <ReAptSearchArea period={period} lang={lang} t={t} />
      <SkeletonList t={t} />
    </>
  )

  if (status === 'error') return (
    <>
      <ReAptSearchArea period={period} lang={lang} t={t} />
      <ErrorState t={t} onRetry={onRetry} />
    </>
  )

  if (status === 'empty') {
    const hasFilter = minPrice != null || maxPrice != null || !!gu || !!dong || !!seg
    return (
      <>
        <ReAptSearchArea period={period} lang={lang} t={t} />
        <div style={{
          borderTop: `1px solid ${C.borderSub}`,
          padding: '56px 28px 60px',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          textAlign: 'center', gap: 13, fontFamily: FONT.sans,
        }}>
          <div style={{
            width: 62, height: 62, borderRadius: 18,
            background: C.surfaceAlt, border: `1px solid ${C.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="28" height="28" viewBox="0 0 28 28">
              <line x1="5" y1="14" x2="23" y2="14" stroke={C.textDim} strokeWidth="2.4" strokeLinecap="round" />
            </svg>
          </div>
          <div style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary }}>
            {hasFilter
              ? (lang === 'ko' ? '조건에 맞는 단지가 없어요' : 'No complexes match the filter')
              : (lang === 'ko' ? '데이터가 없어요' : 'No data available')}
          </div>
          <div style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.5, maxWidth: 260 }}>
            {hasFilter
              ? (lang === 'ko'
                  ? '이 동네는 조용하네요. (거래가 없다는 뜻이에요)'
                  : 'Pretty quiet around here. (Meaning: no transactions.)')
              : (lang === 'ko'
                  ? '배치가 아직 실행되지 않았거나, 해당 지역·기간에 데이터가 없어요.'
                  : 'Batch not yet run, or no data for this region and period.')}
          </div>
          {hasFilter && (
            <button
              onClick={onResetFilters}
              style={{ marginTop: 6, padding: '10px 20px', border: `1px solid ${C.border}`, borderRadius: 11, background: 'transparent', color: C.textSub, fontSize: 13, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer' }}
            >
              {lang === 'ko' ? '필터 초기화' : 'Reset filters'}
            </button>
          )}
        </div>
      </>
    )
  }

  if (rankings.length === 0) {
    const hasFilter = minPrice != null || maxPrice != null || !!gu || !!dong || !!seg
    return (
      <>
        <ReAptSearchArea period={period} lang={lang} t={t} />
        <div style={{
          borderTop: `1px solid ${C.borderSub}`,
          padding: '56px 28px 40px',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          textAlign: 'center', gap: 13, fontFamily: FONT.sans,
        }}>
          <div style={{
            width: 62, height: 62, borderRadius: 18,
            background: C.surfaceAlt, border: `1px solid ${C.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="28" height="28" viewBox="0 0 28 28">
              <line x1="5" y1="14" x2="23" y2="14" stroke={C.textDim} strokeWidth="2.4" strokeLinecap="round" />
            </svg>
          </div>
          <div style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary }}>
            {hasFilter
              ? (lang === 'ko' ? '조건에 맞는 단지가 없어요' : 'No complexes match the filter')
              : (lang === 'ko' ? '데이터가 없어요' : 'No data available')}
          </div>
          <div style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.5, maxWidth: 260 }}>
            {hasFilter
              ? (lang === 'ko'
                  ? '이 동네는 조용하네요. (거래가 없다는 뜻이에요)'
                  : 'Pretty quiet around here. (Meaning: no transactions.)')
              : (lang === 'ko'
                  ? '배치가 아직 실행되지 않았거나, 해당 지역·기간에 데이터가 없어요.'
                  : 'Batch not yet run, or no data for this region and period.')}
          </div>
          {hasFilter && (
            <button
              onClick={onResetFilters}
              style={{ marginTop: 6, padding: '10px 20px', border: `1px solid ${C.border}`, borderRadius: 11, background: 'transparent', color: C.textSub, fontSize: 13, fontWeight: 600, fontFamily: FONT.sans, cursor: 'pointer' }}
            >
              {lang === 'ko' ? '필터 초기화' : 'Reset filters'}
            </button>
          )}
        </div>
        {excluded.length > 0 && (
          <ReResultArea rankings={[]} excluded={excluded} meta={null} lang={lang} period={period} />
        )}
      </>
    )
  }

  return (
    <>
      <ReAptSearchArea period={period} lang={lang} t={t} />
      <ReResultArea rankings={rankings} excluded={excluded} meta={meta} lang={lang} period={period} />
    </>
  )
}
