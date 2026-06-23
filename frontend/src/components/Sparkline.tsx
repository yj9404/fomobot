interface Props {
  data: number[]
  width: number
  height: number
  color: string
  fill: string
}

function buildPoints(data: number[], w: number, h: number): string {
  const mn = Math.min(...data)
  const mx = Math.max(...data)
  const range = mx - mn || 1
  const dx = w / (data.length - 1)
  return data
    .map((y, i) => `${(i * dx).toFixed(1)},${(h - 2 - ((y - mn) / range) * (h - 4)).toFixed(1)}`)
    .join(' ')
}

export function Sparkline({ data, width, height, color, fill }: Props) {
  if (data.length < 2) return null
  const line = buildPoints(data, width, height)
  const area = `${line} ${width},${height} 0,${height}`

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      style={{ flex: 1, minWidth: 0, display: 'block' }}
    >
      <polygon points={area} fill={fill} />
      <polyline points={line} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
    </svg>
  )
}

/** Deterministic pseudo-random sparkline seeded by a string */
export function buildSparkSeries(seed: string, endRet: number, n = 22): number[] {
  let x = 2166136261 >>> 0
  for (let i = 0; i < seed.length; i++) {
    x ^= seed.charCodeAt(i)
    x = Math.imul(x, 16777619) >>> 0
  }
  const rnd = () => { x = (Math.imul(x, 1664525) + 1013904223) >>> 0; return x / 4294967296 }
  let v = 100
  const a = [v]
  const step = endRet / 100 / (n - 1)
  for (let i = 1; i < n; i++) { v = v * (1 + step + (rnd() - 0.5) * 0.045); a.push(v) }
  return a
}
