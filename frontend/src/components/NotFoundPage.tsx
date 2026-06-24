import { useState } from 'react'
import { C, FONT } from '../tokens'

const STR = {
  ko: {
    title: '이 페이지는 상장폐지됐어요',
    sub: '찾으시는 페이지가 명예의 전당에서 사라졌거나, 주소를 잘못 입력하셨어요. 거래가 정지된 종목처럼요.',
    quip: '없는 걸 찾으셨네요. FomoBot 전문 분야인데.',
    home: '홈으로 돌아가기',
    back: '이전 페이지',
    foot: 'ERROR 404 · PAGE NOT FOUND',
  },
  en: {
    title: 'This page got delisted',
    sub: 'The page you are looking for vanished from the hall of fame, or the address is wrong. Like a halted ticker.',
    quip: "You found something that does not exist. FomoBot specialty.",
    home: 'Back to home',
    back: 'Go back',
    foot: 'ERROR 404 · PAGE NOT FOUND',
  },
} as const

type Lang = 'ko' | 'en'

// Deterministic up-then-crash sparkline points over 320×120
const CRASH_PTS = [18, 12, 26, 16, 34, 22, 40, 30, 52, 44, 70, 108, 96, 118]
const W = 320, H = 120
const dx = W / (CRASH_PTS.length - 1)
const linePts = CRASH_PTS.map((y, i) => `${(i * dx).toFixed(1)},${y.toFixed(1)}`).join(' ')
const areaPts = linePts + ` ${W},${H} 0,${H}`

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
    background: active ? '#2A3346' : 'transparent',
    color: active ? C.textPrimary : C.textDim,
  }
}

export function NotFoundPage() {
  const [lang, setLang] = useState<Lang>('ko')
  const t = STR[lang]

  function goBack() {
    if (typeof history !== 'undefined' && history.length > 1) history.back()
    else window.location.href = '/'
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 32,
      background: `radial-gradient(1100px 640px at 50% -12%, rgba(62,123,250,0.18), ${C.bg} 62%), ${C.bg}`,
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
            background: '#11151D',
            border: `1px solid rgba(255,255,255,0.07)`,
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
          boxShadow: '0 28px 70px rgba(0,0,0,0.6)',
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
            <span style={{ fontSize: 12, fontWeight: 700, color: C.textDim, letterSpacing: '0.08em' }}>FOMO:PAGE</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, fontWeight: 700, color: C.red }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%',
                background: C.red,
                animation: 'fb-pulse 1.3s infinite',
              }} />
              HALTED
            </span>
          </div>

          <div style={{ padding: '46px 32px 40px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18 }}>

            {/* 404 + crash sparkline */}
            <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg
                width="100%" height="120" viewBox="0 0 320 120"
                preserveAspectRatio="none"
                style={{ position: 'absolute', inset: 0, opacity: 0.5 }}
              >
                <polygon points={areaPts} fill="rgba(62,123,250,0.10)" />
                <polyline
                  points={linePts}
                  fill="none"
                  stroke="#3E7BFA"
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
                background: 'linear-gradient(135deg,#7AA2FF,#21D4D4)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>404</div>
            </div>

            <div style={{ fontSize: 23, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.01em', marginTop: 6 }}>
              {t.title}
            </div>
            <div style={{ fontSize: 14.5, color: C.textMuted, lineHeight: 1.6, maxWidth: 380 }}>
              {t.sub}
            </div>
            <div style={{ fontSize: 13, color: C.textDim, fontStyle: 'italic' }}>
              "{t.quip}"
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10, marginTop: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
              <a
                href="/"
                style={{
                  textDecoration: 'none',
                  padding: '12px 24px',
                  borderRadius: 12,
                  background: 'linear-gradient(135deg,#3E7BFA,#2F66E0)',
                  color: '#fff',
                  fontSize: 14,
                  fontWeight: 700,
                  whiteSpace: 'nowrap',
                  boxShadow: '0 4px 16px rgba(62,123,250,0.38)',
                }}
              >
                {t.home}
              </a>
              <button
                onClick={goBack}
                style={{
                  padding: '12px 24px',
                  border: `1px solid rgba(255,255,255,0.13)`,
                  borderRadius: 12,
                  background: 'transparent',
                  color: C.textSub,
                  fontSize: 14,
                  fontWeight: 600,
                  fontFamily: 'inherit',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {t.back}
              </button>
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
