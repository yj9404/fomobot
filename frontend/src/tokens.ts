export type Theme = 'dark' | 'light'

export type Colors = {
  bg: string
  surface: string
  surfaceUp: string
  surfaceAlt: string
  surfaceBt: string

  border: string
  borderSub: string
  borderFaint: string

  textPrimary: string
  textSub: string
  textMuted: string
  textDim: string

  green: string
  red: string
  orange: string
  orangeAlt: string
  blue: string
  blueAlt: string
  blueSoft: string

  greenFill: string
  redFill: string
  blueFill: string
  orangeFill: string

  shimmerBase: string
  shimmerHighlight: string
  cardGradient: string
  cardBorderDefault: string
  langBg: string
  langActive: string
  langBorder: string
  hoverBg: string
  barTrack: string
  inputBg: string
  inputBorder: string
}

export const DARK: Colors = {
  bg:         '#0B0D12',
  surface:    '#0A0C10',
  surfaceUp:  '#12161F',
  surfaceAlt: '#0F131B',
  surfaceBt:  '#0B0F18',

  border:      'rgba(255,255,255,0.08)',
  borderSub:   'rgba(255,255,255,0.06)',
  borderFaint: 'rgba(255,255,255,0.05)',

  textPrimary: '#E9EDF5',
  textSub:     '#C7CEDC',
  textMuted:   '#9AA5B8',
  textDim:     '#7C8699',

  green:     '#1ECB81',
  red:       '#FF4D62',
  orange:    '#F4A93C',
  orangeAlt: '#FF8A4C',
  blue:      '#3E7BFA',
  blueAlt:   '#2F66E0',
  blueSoft:  '#7AA2FF',

  greenFill:  'rgba(30,203,129,0.15)',
  redFill:    'rgba(255,77,98,0.15)',
  blueFill:   'rgba(62,123,250,0.08)',
  orangeFill: 'rgba(244,169,60,0.06)',

  shimmerBase:      '#161B26',
  shimmerHighlight: '#222B3A',
  cardGradient:     'linear-gradient(180deg,#12161F,#0F131B)',
  cardBorderDefault:'rgba(255,255,255,0.07)',
  langBg:           '#11151D',
  langActive:       '#2A3346',
  langBorder:       'rgba(255,255,255,0.07)',
  hoverBg:          'rgba(255,255,255,0.025)',
  barTrack:         'rgba(255,255,255,0.06)',
  inputBg:          '#1B2130',
  inputBorder:      'rgba(255,255,255,0.20)',
}

export const LIGHT: Colors = {
  bg:         '#EEF0F7',
  surface:    '#FFFFFF',
  surfaceUp:  '#E4E7F2',
  surfaceAlt: '#F3F4FA',
  surfaceBt:  '#F8F9FC',

  border:      'rgba(0,0,0,0.10)',
  borderSub:   'rgba(0,0,0,0.08)',
  borderFaint: 'rgba(0,0,0,0.05)',

  textPrimary: '#111827',
  textSub:     '#374151',
  textMuted:   '#6B7280',
  textDim:     '#9CA3AF',

  green:     '#16A34A',
  red:       '#DC2626',
  orange:    '#D97706',
  orangeAlt: '#EA580C',
  blue:      '#2563EB',
  blueAlt:   '#1D4ED8',
  blueSoft:  '#3B82F6',

  greenFill:  'rgba(22,163,74,0.10)',
  redFill:    'rgba(220,38,38,0.10)',
  blueFill:   'rgba(37,99,235,0.07)',
  orangeFill: 'rgba(217,119,6,0.08)',

  shimmerBase:      '#E2E6F0',
  shimmerHighlight: '#EEF0F8',
  cardGradient:     'linear-gradient(180deg,#F8F9FC,#F2F4F9)',
  cardBorderDefault:'rgba(0,0,0,0.08)',
  langBg:           '#E8EBF5',
  langActive:       '#D6DCF0',
  langBorder:       'rgba(0,0,0,0.09)',
  hoverBg:          'rgba(0,0,0,0.03)',
  barTrack:         'rgba(0,0,0,0.07)',
  inputBg:          '#FFFFFF',
  inputBorder:      'rgba(0,0,0,0.18)',
}

// bg/surface — 파란 틴트 제거 + warm-dark 방향으로 더 뚜렷하게 이동.
// 의미색(green/red/orange*)은 건드리지 않음.
export const DARK_DECLINE_OVERRIDE: Partial<Colors> = {
  bg:               '#120A12',
  surface:          '#0F080F',
  surfaceUp:        '#1B1020',
  surfaceAlt:       '#180D1A',
  surfaceBt:        '#140B16',
  shimmerBase:      '#1D1224',
  shimmerHighlight: '#251827',
  cardGradient:     'linear-gradient(180deg,#1B1020,#180D1A)',
  cardBorderDefault:'rgba(255,255,255,0.07)',
}

export const LIGHT_DECLINE_OVERRIDE: Partial<Colors> = {
  bg:               '#EDE8ED',
  surfaceUp:        '#E0D9E2',
  surfaceAlt:       '#EDE8EE',
  surfaceBt:        '#F3EEF4',
  shimmerBase:      '#E0D9E2',
  shimmerHighlight: '#E9E3EA',
  cardGradient:     'linear-gradient(180deg,#F3EEF4,#EDE8EE)',
}

// 앵커 요소(토글 활성, 순위 배지, 헤더선, 로고 glow)에 쓰는 하락 모드 색.
// bg/surface override와 별개로 관리 — 의미색과 충돌하지 않음.
export const DECLINE_ACCENT_DARK = {
  activeBg:     'rgba(255,77,98,0.13)',
  activeText:   '#FF8C9E',
  activeBorder: 'rgba(255,77,98,0.38)',
  badgeBg:      'rgba(255,77,98,0.12)',
  badgeText:    '#FF8C9E',
  badgeBorder:  'rgba(255,77,98,0.38)',
  headerLine:   'rgba(255,77,98,0.22)',
  logoShadow:   '0 0 0 1px rgba(255,77,98,0.32), 0 4px 14px rgba(255,77,98,0.40)',
} as const

export const DECLINE_ACCENT_LIGHT = {
  activeBg:     'rgba(185,28,28,0.09)',
  activeText:   '#B91C1C',
  activeBorder: 'rgba(185,28,28,0.30)',
  badgeBg:      'rgba(185,28,28,0.08)',
  badgeText:    '#B91C1C',
  badgeBorder:  'rgba(185,28,28,0.30)',
  headerLine:   'rgba(185,28,28,0.20)',
  logoShadow:   '0 0 0 1px rgba(185,28,28,0.26), 0 4px 14px rgba(185,28,28,0.28)',
} as const

export type DeclineAccent = typeof DECLINE_ACCENT_DARK

export const FONT = {
  sans: "'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
  mono: "'JetBrains Mono', monospace",
} as const
