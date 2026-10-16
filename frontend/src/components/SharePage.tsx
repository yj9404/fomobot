import { useEffect, useState } from 'react'
import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { useAdGate } from '../hooks/useAdGate'
import { Footer } from './Footer'
import { fetchShareCard, type ShareCardResult } from '../api/share'
import { cardFileName, decideSaveMode } from '../utils/cardImage'
import {
  daysBetween, fmtSharePct, parseShareParams, shareQuery,
  type ShareData, type ShareParams,
} from '../../shared/share'

/**
 * 공유 랜딩 /s/{market}/{ticker}?from&to.
 *
 * OG 메타는 Worker가 index.html에 이미 주입했으므로 여기서는 화면만 그린다.
 * 페이지 자체는 noindex이고(Worker가 meta robots + X-Robots-Tag), sitemap에도 없다.
 * 광고는 멈춘다 — 종목·기간 조합마다 생기는 얇은 페이지라 자동 생성 페이지로
 * 판정될 위험을 피하기 위함이다.
 */

type State = { status: 'loading' } | ShareCardResult

function readParams(): ShareParams | null {
  const m = window.location.pathname.match(/^\/s\/([^/]+)\/([^/]+)\/?$/)
  if (!m) return null
  // 티커 정규식이 %를 허용하지 않으므로 디코딩하지 않는다(잘못된 % 인코딩에서 예외 방지).
  return parseShareParams(m[1]!, m[2]!, new URLSearchParams(window.location.search))
}

export function SharePage() {
  const C = useC()
  const [params] = useState(readParams)
  const [state, setState] = useState<State>(params ? { status: 'loading' } : { status: 'invalid' })
  const [retryKey, setRetryKey] = useState(0)
  useAdGate(false)

  useEffect(() => {
    if (!params) return
    const ctrl = new AbortController()
    setState({ status: 'loading' })
    fetchShareCard(params, ctrl.signal)
      .then(setState)
      .catch(() => { /* unmount로 인한 abort */ })
    return () => ctrl.abort()
  }, [params, retryKey])

  return (
    <div style={{ minHeight: '100vh', background: C.bg, fontFamily: FONT.sans, display: 'flex', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: 640, display: 'flex', flexDirection: 'column', padding: '20px 16px 0' }}>
        <a href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', marginBottom: 20 }}>
          <div style={{ width: 26, height: 26, borderRadius: 8, background: 'linear-gradient(135deg,#3E7BFA,#21D4D4)' }} />
          <span style={{ fontSize: 18, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.02em' }}>FomoBot</span>
        </a>

        <main style={{ flex: 1 }}>
          {state.status === 'loading' && <Loading />}
          {state.status === 'invalid' && (
            <Notice
              title="유효하지 않은 공유 링크"
              sub="주소가 잘못됐거나 더 이상 제공되지 않는 카드입니다."
            />
          )}
          {state.status === 'unavailable' && (
            <Notice
              title="일시적으로 불러올 수 없습니다"
              sub="잠시 후 다시 시도해 주세요."
              onRetry={() => setRetryKey((k) => k + 1)}
            />
          )}
          {state.status === 'ok' && params && <ShareCard d={state.data} p={params} />}
        </main>

        <Footer lang="ko" style={{ padding: '24px 0 28px', marginTop: 28, borderTop: `1px solid ${C.borderSub}` }} />
      </div>
    </div>
  )
}

function ShareCard({ d, p }: { d: ShareData; p: ShareParams }) {
  const C = useC()
  const pct = fmtSharePct(d.return_pct)
  // 같은 기간 길이를 오늘(최신 거래일) 기준으로 다시 본다 — StockSearchArea 딥링크.
  const replayHref = `/?market=${p.market}&ticker=${encodeURIComponent(p.ticker)}&days=${daysBetween(p.from, p.to)}`
  const imageUrl = `/og/${p.market}/${p.ticker}.png${shareQuery(p)}`

  return (
    <article style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* 길게 눌러 저장할 수 있어야 하므로 이미지 위에 오버레이나 pointer-events 차단을 두지 않는다 */}
      <img
        src={imageUrl}
        alt={`${d.name} ${pct} (${d.from}~${d.to}) 공유 카드`}
        width={1200}
        height={630}
        style={{ width: '100%', height: 'auto', borderRadius: 14, border: `1px solid ${C.border}`, display: 'block' }}
      />

      <SaveImage p={p} imageUrl={imageUrl} />

      {/* 숫자는 카드 이미지에 이미 있으므로 텍스트로 반복하지 않는다. 화면 낭독기용 제목만 둔다. */}
      <h1 style={visuallyHidden}>{`${d.name} ${pct} (${d.from}~${d.to})`}</h1>
      <p style={{ fontSize: 12.5, color: C.textMuted, textAlign: 'center' }}>
        {d.to} 종가 기준 스냅샷입니다. 이후 가격 변동은 반영되지 않습니다.
      </p>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <a href={replayHref} style={ctaStyle(C.blue, '#fff', 'transparent')}>오늘 기준으로 다시 보기</a>
        <a href="/" style={ctaStyle('transparent', C.textSub, C.border)}>다른 종목으로 해보기</a>
      </div>

      <section style={{ fontSize: 12, lineHeight: 1.7, color: C.textMuted, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <p>
          <strong style={{ color: C.textSub }}>데이터 기준</strong> — {d.from} 종가에 전액 매수해 {d.to} 종가까지
          보유했다고 가정한 수익률입니다. 거래비용과 세금은 반영하지 않았습니다.
        </p>
        <p>
          <strong style={{ color: C.textSub }}>배당 처리</strong> — 현금배당을 반영하지 않은 가격 수익률입니다.
          실제 보유 수익은 배당만큼 더 높았을 수 있습니다(<a href="/glossary#수정주가" style={{ color: C.blueSoft }}>용어 해설</a>).
        </p>
        {d.currency === 'USD' && (
          <p>
            <strong style={{ color: C.textSub }}>환율</strong> — 달러 기준 수익률이며, 원화로 환산했을 때의 환율 변동은 반영하지 않았습니다.
          </p>
        )}
        <p>
          <strong style={{ color: C.textSub }}>생존 편향</strong> — 상장폐지된 종목은 데이터에 포함되지 않으므로
          이런 수치들은 실제 시장보다 낙관적입니다. <a href="/survivorship-bias" style={{ color: C.blueSoft }}>생존 편향 안내</a>를 참고하십시오.
        </p>
        <p>
          <strong style={{ color: C.textSub }}>투자 판단에 대하여</strong> — FomoBot은 이미 지나간 가격을 정리해 보여주는
          도구입니다. 특정 종목의 매수·매도를 권유하지 않으며, 이 카드의 어떤 내용도 투자 자문이 아닙니다.
          투자 손익의 책임은 투자자 본인에게 있습니다.
        </p>
      </section>
    </article>
  )
}

/**
 * 카드 이미지 저장. PNG는 페이지 로드 때 미리 blob으로 받아 둔다 — 클릭 후에 fetch하면
 * Safari가 사용자 제스처가 끝났다고 보고 navigator.share를 막는다.
 */
function SaveImage({ p, imageUrl }: { p: ShareParams; imageUrl: string }) {
  const C = useC()
  const [file, setFile] = useState<File | null>(null)
  const [settled, setSettled] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    fetch(imageUrl, { signal: ctrl.signal })
      .then((r) => (r.ok && (r.headers.get('content-type') ?? '').startsWith('image/png') ? r.blob() : null))
      .then((blob) => {
        setFile(blob ? new File([blob], cardFileName(p), { type: 'image/png' }) : null)
        setSettled(true)
      })
      .catch((e: unknown) => {
        if (e instanceof DOMException && e.name === 'AbortError') return
        setSettled(true)
      })
    return () => ctrl.abort()
  }, [imageUrl, p])

  if (!settled) return null

  const mode = decideSaveMode({
    hasBlob: file != null,
    userAgent: navigator.userAgent,
    maxTouchPoints: navigator.maxTouchPoints,
    canShareFiles: file != null && navigator.canShare?.({ files: [file] }) === true,
  })

  if (mode === 'long-press' || file == null) {
    return (
      <p style={{ fontSize: 12.5, color: C.textSub, textAlign: 'center' }}>
        이미지를 길게 눌러 저장하세요
      </p>
    )
  }

  async function save(f: File) {
    if (mode === 'share-file') {
      try {
        await navigator.share({ files: [f] })
        return
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') return
        // NotAllowedError 등은 다운로드로 폴백
      }
    }
    const href = URL.createObjectURL(f)
    const a = document.createElement('a')
    a.href = href
    a.download = f.name
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(href), 1000)
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center' }}>
      <button
        onClick={() => save(file)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 700,
          fontFamily: 'inherit', cursor: 'pointer',
          background: 'rgba(62,123,250,0.12)', color: C.blueSoft,
          border: '1px solid rgba(62,123,250,0.35)',
        }}
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M8 2v8" />
          <path d="M5 7l3 3 3-3" />
          <path d="M3 11v2a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1v-2" />
        </svg>
        이미지 저장
      </button>
    </div>
  )
}

const visuallyHidden: React.CSSProperties = {
  position: 'absolute', width: 1, height: 1, padding: 0, margin: -1,
  overflow: 'hidden', clip: 'rect(0 0 0 0)', whiteSpace: 'nowrap', border: 0,
}

function ctaStyle(bg: string, fg: string, border: string): React.CSSProperties {
  return {
    flex: '1 1 200px', textAlign: 'center', textDecoration: 'none',
    padding: '12px 18px', borderRadius: 12, fontSize: 14, fontWeight: 700,
    background: bg, color: fg, border: `1px solid ${border}`,
  }
}

function Loading() {
  const C = useC()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '40px 0', justifyContent: 'center' }}>
      <div style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid rgba(62,123,250,0.25)', borderTopColor: C.blue, animation: 'fb-spin .8s linear infinite' }} />
      <span style={{ fontSize: 13, color: C.textDim }}>불러오는 중…</span>
    </div>
  )
}

function Notice({ title, sub, onRetry }: { title: string; sub: string; onRetry?: () => void }) {
  const C = useC()
  return (
    <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 14, padding: '36px 20px', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
      <h1 style={{ fontSize: 20, fontWeight: 800, color: C.textPrimary }}>{title}</h1>
      <p style={{ fontSize: 13.5, color: C.textMuted }}>{sub}</p>
      <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        {onRetry && (
          <button onClick={onRetry} style={{ ...ctaStyle(C.blue, '#fff', 'transparent'), flex: 'none', cursor: 'pointer', fontFamily: 'inherit' }}>
            다시 시도
          </button>
        )}
        <a href="/" style={{ ...ctaStyle(onRetry ? 'transparent' : C.blue, onRetry ? C.textSub : '#fff', onRetry ? C.border : 'transparent'), flex: 'none' }}>
          홈으로
        </a>
      </div>
    </div>
  )
}
