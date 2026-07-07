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
