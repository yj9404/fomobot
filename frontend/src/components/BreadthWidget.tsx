import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { useBreadth } from '../hooks/useBreadth'
import type { Market } from '../types'
import type { Strings } from '../i18n/strings'

interface Props {
  market: Market
  t: Strings
}

/**
 * 데이터가 없으면(백필 전, 배치 미실행 등) 아무것도 렌더링하지 않는다.
 * 에러 문구·스켈레톤·"데이터 준비 중" 같은 플레이스홀더를 일부러 두지 않았다 —
 * 배포 순서상 백필이 끝나기 전에 프론트가 먼저 뜨는 시간대가 있을 수 있어서,
 * 그 구간에는 위젯 자체가 없는 것처럼 보이는 편이 낫다고 판단했다.
 */
export function BreadthWidget({ market, t }: Props) {
  const C = useC()
  const data = useBreadth(market)

  if (data == null) return null

  const { advancers, decliners, unchanged, date } = data
  const base = advancers + decliners + unchanged
  const declineRatio = base > 0 ? decliners / base : 0

  const mood = declineRatio >= 0.55
    ? t.breadthPanic
    : declineRatio <= 0.40
      ? t.breadthFomo
      : t.breadthNeutral

  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 10, padding: '10px 14px', borderBottom: `1px solid ${C.borderSub}`,
        fontFamily: FONT.sans, flexWrap: 'wrap', rowGap: 4,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, fontFamily: FONT.mono, fontSize: 12 }}>
        <span style={{ color: C.green, fontWeight: 700 }}>{t.breadthUp} {advancers}</span>
        <span style={{ color: C.red, fontWeight: 700 }}>{t.breadthDown} {decliners}</span>
        <span style={{ color: C.textDim, fontWeight: 600 }}>{t.breadthFlat} {unchanged}</span>
        <span style={{ color: C.textDim }}>{date}</span>
      </div>
      <div style={{ fontSize: 12, color: C.textSub, fontWeight: 600 }}>
        {mood}
      </div>
    </div>
  )
}
