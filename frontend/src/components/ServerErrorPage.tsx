import { useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { useAdGate } from '../hooks/useAdGate'

const STR = {
  ko: {
    title: '서버가 차트 보다 넘어졌어요',
    sub: 'FomoBot이 후회 거리를 너무 열심히 계산하다 과부하가 왔어요. 잠시 후 다시 시도해 주세요.',
    code: '500 · INTERNAL',
    quip: 'FomoBot도 가끔은 손절이 필요해요.',
    retry: '다시 시도',
    home: '홈으로',
    status: '엔지니어가 이미 달려가고 있어요',
    foot: 'ERROR 500 · INTERNAL SERVER ERROR',
  },
  en: {
    title: 'The server tripped over a chart',
    sub: 'FomoBot overloaded while calculating your regrets a little too hard. Please try again in a moment.',
    code: '500 · INTERNAL',
    quip: 'Even FomoBot needs a stop-loss sometimes.',
    retry: 'Try again',
    home: 'Home',
    status: 'Engineers are already on it',
    foot: 'ERROR 500 · INTERNAL SERVER ERROR',
  },
} as const

type Lang = 'ko' | 'en'

const CRASH_PTS = [16, 28, 20, 40, 30, 52, 38, 62, 74, 58, 88, 72, 104, 118]
const W = 320, H = 120
const dx = W / (CRASH_PTS.length - 1)
const linePts = CRASH_PTS.map((y, i) => `${(i * dx).toFixed(1)},${y.toFixed(1)}`).join(' ')
const areaPts = linePts + ` ${W},${H} 0,${H}`

export function ServerErrorPage() {
  const [lang, setLang] = useState<Lang>('ko')
  const C = useC()
  const t = STR[lang]
  useAdGate(false)

  function pill(active: boolean): React.CSSProperties {
    return {
      padding: '5px 11px',
      border: 'none',
      borderRadius: 7,
      fontSize: 11,
      fontWeight: 700,
      fontFamily: 'inherit',
      cursor: 'pointer',
      letterSpacing: '0.04em',
      background: active ? C.langActive : 'transparent',
      color: active ? C.textPrimary : C.textDim,
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 32,
      background: `radial-gradient(1100px 640px at 50% -12%, rgba(255,77,98,0.16), ${C.bg} 62%), ${C.bg}`,
      fontFamily: FONT.sans,
    }}>
      <div style={{ width: '100%', maxWidth: 560, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>

        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 11, marginBottom: 44 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 9,
            background: 'linear-gradient(135deg,#3E7BFA,#21D4D4)',
            boxShadow: `0 0 0 1px rgba(62,123,250,0.3), 0 6px 18px rgba(62,123,250,0.4)`,
          }} />
          <div style={{ fontSize: 21, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.02em' }}>FomoBot</div>
          <div style={{
            display: 'flex',
            background: C.langBg,
            border: `1px solid ${C.langBorder}`,
            borderRadius: 9,
            padding: 2,
            gap: 2,
            marginLeft: 4,
          }}>
            <button onClick={() => setLang('ko')} style={pill(lang === 'ko')}>KO</button>
            <button onClick={() => setLang('en')} style={pill(lang === 'en')}>EN</button>
          </div>
        </div>

        {/* Ticker card */}
        <div style={{
          width: '100%',
          background: C.surface,
          border: `1px solid ${C.border}`,
          borderRadius: 24,
          overflow: 'hidden',
          boxShadow: '0 28px 70px rgba(0,0,0,0.4)',
        }}>

          {/* Fake ticker tape */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '13px 18px',
            borderBottom: `1px solid ${C.borderSub}`,
            fontFamily: FONT.mono,
          }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: C.textDim, letterSpacing: '0.08em' }}>FOMO:SERVER</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 700, color: C.red }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%',
                background: C.red,
                animation: 'fb-pulse 1.1s infinite',
              }} />
              CIRCUIT BREAKER
            </span>
          </div>

          <div style={{ padding: '46px 32px 40px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18 }}>

            {/* 500 + crash sparkline */}
            <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg
                width="100%" height="120" viewBox="0 0 320 120"
                preserveAspectRatio="none"
                style={{ position: 'absolute', inset: 0, opacity: 0.55 }}
              >
                <polygon points={areaPts} fill="rgba(255,77,98,0.10)" />
                <polyline
                  points={linePts}
                  fill="none"
                  stroke={C.red}
                  strokeWidth="2.5"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  strokeDasharray="640"
                  style={{ animation: 'fb-draw 1.6s ease-out both' }}
                />
              </svg>
              <div style={{
                position: 'relative',
                fontFamily: FONT.mono,
                fontSize: 104,
                fontWeight: 800,
                lineHeight: 1,
                letterSpacing: '-0.03em',
                background: 'linear-gradient(135deg,#FF8A4C,#FF4D62)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>500</div>
            </div>

            <div style={{ fontSize: 23, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.01em', marginTop: 6 }}>
              {t.title}
            </div>
            <div style={{ fontSize: 14.5, color: C.textMuted, lineHeight: 1.6, maxWidth: 380 }}>
              {t.sub}{' '}
              <span style={{ fontFamily: FONT.mono, color: C.textDim, fontSize: 12 }}>{t.code}</span>
            </div>
            <div style={{ fontSize: 13, color: C.textDim, fontStyle: 'italic' }}>
              "{t.quip}"
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10, marginTop: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
              <button
                onClick={() => window.location.reload()}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 9,
                  padding: '12px 24px',
                  border: 'none',
                  borderRadius: 12,
                  background: 'linear-gradient(135deg,#3E7BFA,#2F66E0)',
                  color: '#fff',
                  fontSize: 14,
                  fontWeight: 700,
                  fontFamily: 'inherit',
                  cursor: 'pointer',
                  boxShadow: '0 4px 16px rgba(62,123,250,0.38)',
                }}
              >
                <span style={{
                  width: 13, height: 13,
                  borderRadius: '50%',
                  border: '2px solid rgba(255,255,255,0.4)',
                  borderTopColor: '#fff',
                  animation: 'fb-spin .8s linear infinite',
                  display: 'inline-block',
                  flexShrink: 0,
                }} />
                {t.retry}
              </button>
              <a
                href="/"
                style={{
                  textDecoration: 'none',
                  padding: '12px 24px',
                  border: `1px solid ${C.border}`,
                  borderRadius: 12,
                  background: 'transparent',
                  color: C.textSub,
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                {t.home}
              </a>
            </div>

            {/* Status indicator */}
            <div style={{ marginTop: 6, fontSize: 11.5, color: C.textDim, display: 'flex', alignItems: 'center', gap: 7 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: C.orange, flexShrink: 0 }} />
              {t.status}
            </div>
          </div>
        </div>

        <div style={{ marginTop: 26, fontSize: 11.5, color: C.textDim, fontFamily: FONT.mono, letterSpacing: '0.04em' }}>
          {t.foot}
        </div>
      </div>
    </div>
  )
}
