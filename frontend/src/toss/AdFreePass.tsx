import { useEffect, useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { TOSS_UI } from '../i18n/strings.toss'
import { getAdFreeUntil, isAdFreeRewardAvailable, preloadAdFreeReward, showAdFreeReward } from './ads'

// 남은 시간 표시는 분 단위라 30초마다 갱신하면 충분하다.
const TICK_MS = 30_000

/** 남은 시간을 "N시간 M분"으로. 분은 올림해 0분이 보이지 않게 한다. */
export function remainingParts(ms: number): { h: number; m: number } {
  const total = Math.max(1, Math.ceil(ms / 60_000))
  return { h: Math.floor(total / 60), m: total % 60 }
}

/**
 * 순위 화면 상단의 광고 제거 이용권. 보상형 광고를 끝까지 보면 24시간 동안 전면광고를 건너뛴다(배너는 그대로).
 * 활성 중에는 남은 시간을 보여준다. 미지원 환경이거나 광고를 불러오지 못하면 영역을 비운다.
 */
export function AdFreePass() {
  const C = useC()
  const [supported] = useState(isAdFreeRewardAvailable)
  const [until, setUntil] = useState<number | null | undefined>(undefined) // undefined = 아직 읽는 중
  const [now, setNow] = useState(() => Date.now())
  const [phase, setPhase] = useState<'loading' | 'ready' | 'showing' | 'unavailable'>('loading')
  const [reloadKey, setReloadKey] = useState(0)
  const active = until != null && until > now

  useEffect(() => {
    if (supported) void getAdFreeUntil().then(setUntil)
  }, [supported])

  useEffect(() => {
    if (!active) return
    const id = setInterval(() => setNow(Date.now()), TICK_MS)
    return () => clearInterval(id)
  }, [active])

  // 이용권이 없을 때만(만료 직후 포함) 광고를 미리 로드한다.
  useEffect(() => {
    if (!supported || until === undefined || active) return
    let cancelled = false
    setPhase('loading')
    void preloadAdFreeReward().then((ok) => { if (!cancelled) setPhase(ok ? 'ready' : 'unavailable') })
    return () => { cancelled = true }
  }, [supported, until, active, reloadKey])

  if (!supported || until === undefined) return null

  const box: React.CSSProperties = {
    display: 'block', width: 'calc(100% - 32px)', margin: '4px 16px 8px', padding: '12px 14px', minHeight: 56,
    borderRadius: 12, border: `1px solid ${C.borderSub}`, background: C.surfaceAlt,
    textAlign: 'left', fontFamily: FONT.sans, boxSizing: 'border-box',
  }

  if (active) {
    const { h, m } = remainingParts(until - now)
    return (
      <div style={box}>
        <div style={{ fontSize: 14, fontWeight: 700, color: C.blueSoft }}>{TOSS_UI.adFreeActive}</div>
        <div style={{ marginTop: 2, fontSize: 12, color: C.textMuted }}>{TOSS_UI.adFreeRemaining(h, m)}</div>
      </div>
    )
  }

  if (phase === 'unavailable') return null

  const onClick = () => {
    setPhase('showing')
    void showAdFreeReward().then((u) => {
      setNow(Date.now())
      setUntil(u)
      setReloadKey((k) => k + 1) // 보상을 못 받았으면 다음 광고를 다시 로드한다.
    })
  }

  const ready = phase === 'ready'
  return (
    <button onClick={onClick} disabled={!ready} style={{ ...box, cursor: ready ? 'pointer' : 'default', opacity: ready ? 1 : 0.6 }}>
      <div style={{ fontSize: 14, fontWeight: 700, color: C.textPrimary }}>{TOSS_UI.adFreeCta}</div>
      <div style={{ marginTop: 2, fontSize: 12, color: C.textMuted }}>{ready ? TOSS_UI.adFreeSub : TOSS_UI.adFreePreparing}</div>
    </button>
  )
}
