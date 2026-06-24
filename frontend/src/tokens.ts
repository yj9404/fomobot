export type Theme = 'dark' | 'light'

export const DARK = {
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
} as const

export const LIGHT = {
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
} as const

export type Colors = typeof DARK | typeof LIGHT

export const FONT = {
  sans: "'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
  mono: "'JetBrains Mono', monospace",
} as const
