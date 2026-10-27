import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { changeColor } from '../tossColors'
import { fmtPrice } from '../format'
import { TOSS_UI } from '../i18n/strings.toss'
import type { Market } from '../types'

interface Props {
  points: [string, number][]
  market: Market
  height?: number
}

const VIEW_W = 1000

/**
 * 종가 선 차트. 최고·최저 지점에만 가격 라벨을 단다 — 특정 날짜를 짚는 터치 툴팁은 두지 않는다.
 * 선은 가로로 늘어나도 굵기가 유지되도록(non-scaling-stroke) SVG에, 라벨은 글자가 늘어나지 않게 HTML에 그린다.
 */
export function PriceChart({ points, market, height = 180 }: Props) {
  const C = useC()
  if (points.length < 2) return null

  const prices = points.map((p) => p[1])
  const lo = Math.min(...prices)
  const hi = Math.max(...prices)
  const span = hi - lo || 1
  const pad = 22 // 라벨 자리
  const plotH = height - pad * 2
  const x = (i: number) => (i / (points.length - 1)) * VIEW_W
  const y = (p: number) => pad + (1 - (p - lo) / span) * plotH
  const line = points.map(([, p], i) => `${x(i).toFixed(1)},${y(p).toFixed(1)}`).join(' ')
  const color = changeColor(prices[prices.length - 1]! - prices[0]!, C.textMuted)

  const hiIdx = prices.indexOf(hi)
  const loIdx = prices.indexOf(lo)
  // 라벨이 화면 밖으로 나가지 않게 가로 위치를 10~90%로 묶는다.
  const leftPct = (i: number) => Math.min(90, Math.max(10, (i / (points.length - 1)) * 100))
  const label: React.CSSProperties = {
    position: 'absolute', transform: 'translateX(-50%)', whiteSpace: 'nowrap',
    fontSize: 11, fontFamily: FONT.mono, color: C.textMuted,
  }

  return (
    <div style={{ position: 'relative', height, margin: '0 16px' }}>
      <svg
        width="100%" height={height} viewBox={`0 0 ${VIEW_W} ${height}`} preserveAspectRatio="none"
        style={{ display: 'block' }} aria-hidden="true"
      >
        <polyline
          points={line} fill="none" stroke={color} strokeWidth={2}
          strokeLinejoin="round" vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div style={{ ...label, top: 0, left: `${leftPct(hiIdx)}%` }}>
        {TOSS_UI.chartHigh} {fmtPrice(hi, market)}
      </div>
      <div style={{ ...label, bottom: 0, left: `${leftPct(loIdx)}%` }}>
        {TOSS_UI.chartLow} {fmtPrice(lo, market)}
      </div>
    </div>
  )
}
