import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { SkeletonList } from '../components/SkeletonList'
import { ErrorState } from '../components/ErrorState'
import { ReResultArea } from '../components/ReResultArea'
import { useRealEstateRankings } from '../hooks/useRealEstateRankings'
import type { Lang, RealEstatePeriod } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  lang: Lang
  period: RealEstatePeriod
  sido: string      // 시도 필터 ('11'=서울 등, ''=수도권 전체)
  retryKey: number
  onRetry: () => void
  t: Strings
}

export function RealEstateView({ lang, period, sido, retryKey, onRetry, t }: Props) {
  const { status, rankings, excluded, meta } = useRealEstateRankings(period, sido, retryKey)
  const C = useC()

  if (status === 'loading') return <SkeletonList t={t} />

  if (status === 'error') return <ErrorState t={t} onRetry={onRetry} />

  if (status === 'empty') return (
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
        fontSize: 26,
      }}>
        🏢
      </div>
      <div style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary }}>
        {lang === 'ko' ? '데이터가 없어요' : 'No data available'}
      </div>
      <div style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.5, maxWidth: 260 }}>
        {lang === 'ko'
          ? '배치가 아직 실행되지 않았거나, 해당 지역·기간에 데이터가 없어요.'
          : 'Batch not yet run, or no data for this region and period.'}
      </div>
    </div>
  )

  return <ReResultArea rankings={rankings} excluded={excluded} meta={meta} lang={lang} />
}
