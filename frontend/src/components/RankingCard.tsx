import { useEffect, useRef, useState } from 'react'
import { useC, useTheme } from '../ThemeContext'
import { FONT, DECLINE_ACCENT_DARK, DECLINE_ACCENT_LIGHT } from '../tokens'
import { BacktestPanel } from './BacktestPanel'
import { NewsDot } from './NewsDot'
import type { RankingItem, Market, Period, Lang, NewsArticle } from '../types'
import type { Strings } from '../i18n/strings'

interface BtDetailEntry {
  status: 'idle' | 'loading' | 'ok' | 'error'
  detail: import('../types').BacktestDetailResponse | null
}

interface NewsEntry {
  status: 'idle' | 'loading' | 'ok' | 'error'
  articles: NewsArticle[]
}

interface Props {
  item: RankingItem
  open: boolean
  market: Market
  days: number
  period: Period
  btDetail: BtDetailEntry
  newsDetail: NewsEntry
  lang: Lang
  t: Strings
  onToggle: () => void
}

function fmtPct(n: number | null): string {
  if (n == null) return 'N/A'
  return (n >= 0 ? '+' : '') + n.toFixed(1) + '%'
}

export function RankingCard({ item, open, market, days, period, btDetail, newsDetail, lang, t, onToggle }: Props) {
  const C = useC()
  const { theme, atmosphereMode } = useTheme()
  const da = theme === 'dark' ? DECLINE_ACCENT_DARK : DECLINE_ACCENT_LIGHT
  const isFall = atmosphereMode === 'fall'
  const showRiskMetrics = period !== '1d'
  const mdd = item.mdd_pct ?? 0
  const vol = item.volatility_annualized_pct ?? 0
  const excess = item.excess_return_vs_index_pct ?? 0
  const mddBar = Math.min(100, Math.abs(mdd)).toFixed(0) + '%'
  const volBar = Math.min(100, Math.abs(vol)).toFixed(0) + '%'

  // halt_resumption 설명 — hover 없는 모바일 대응으로 tap-toggle(팝오버 라이브러리
  // 없이 useState만). 카드 전체가 overflow:hidden이라 플로팅 박스가 잘리므로
  // (RankingTable과 달리) 절대위치 대신 카드 하단에 인라인으로 확장한다.
  const [haltInfoOpen, setHaltInfoOpen] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!haltInfoOpen) return
    // 'click'을 쓴다(mousedown 아님) — 이 설명 블록은 카드 하단에 인라인으로
    // 확장되므로 닫히면 아래 카드들이 위로 당겨진다(레이아웃 시프트). mousedown
    // 시점에 먼저 닫아버리면 그 직후 발생하는 click이 시프트된 레이아웃 기준
    // 좌표로 처리돼 사용자가 실제로 누른 다른 카드의 버튼을 놓친다(다른 카드가
    // 안 열림). click으로 통일하면 React가 같은 이벤트 디스패치 안에서 다른
    // 카드의 onClick(먼저, 원래 좌표 기준)과 이 정리 로직(나중)을 함께
    // 처리하므로 레이아웃 시프트가 끼어들 틈이 없다.
    const handler = (e: MouseEvent) => {
      if (cardRef.current && !cardRef.current.contains(e.target as Node)) {
        setHaltInfoOpen(false)
      }
    }
    document.addEventListener('click', handler)
    return () => document.removeEventListener('click', handler)
  }, [haltInfoOpen])

  return (
    <div ref={cardRef} style={{
      marginBottom: 10, borderRadius: 16, overflow: 'hidden',
      border: `1px solid ${open ? 'rgba(62,123,250,0.35)' : C.cardBorderDefault}`,
      background: C.cardGradient,
      fontFamily: FONT.sans,
    }}>
      {/* Card header button */}
      <button
        onClick={onToggle}
        style={{ width: '100%', border: 'none', background: 'transparent', cursor: 'pointer', textAlign: 'left', padding: '14px 14px 13px', display: 'block', fontFamily: FONT.sans }}
      >
        {/* Top row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
          <span style={{
            fontFamily: FONT.mono, fontSize: 12, fontWeight: 700,
            color: isFall ? da.badgeText : C.blueSoft,
            background: isFall ? da.badgeBg : 'rgba(62,123,250,0.12)',
            width: 26, height: 26, borderRadius: 8,
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            {String(item.rank).padStart(2, '0')}
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <NewsDot show={item.has_news === true} t={t} />
              <span style={{ fontSize: 15.5, fontWeight: 700, color: C.textPrimary, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {item.name ?? item.ticker}
              </span>
            </div>
            <div style={{ fontFamily: FONT.mono, fontSize: 11, color: C.textDim, marginTop: 2 }}>{item.ticker}</div>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 4 }}>
              {item.halt_resumption === true && (
                <span
                  onClick={(e) => {
                    e.stopPropagation()
                    e.preventDefault()
                    setHaltInfoOpen((v) => !v)
                  }}
                  style={{
                    fontSize: 12, lineHeight: 1, cursor: 'pointer', flexShrink: 0,
                    color: C.textDim, padding: 2,
                  }}
                >
                  ⓘ
                </span>
              )}
              <div style={{ fontFamily: FONT.mono, fontSize: 20, fontWeight: 800, color: item.return_pct >= 0 ? C.green : C.red, lineHeight: 1, letterSpacing: '-0.02em' }}>
                {fmtPct(item.return_pct)}
              </div>
            </div>
            <div style={{ fontSize: 9.5, color: C.textDim, marginTop: 4 }}>{t.moveLabel}</div>
          </div>
        </div>

        {/* Bar row — 전일(1d)은 MDD·변동성이 통계적으로 의미 없어 바 자체를 숨김 */}
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, marginTop: 13 }}>
          {showRiskMetrics && (
            <>
              {/* MDD bar */}
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 5 }}>
                  <span style={{ color: C.textMuted }}>MDD</span>
                  <span style={{ fontFamily: FONT.mono, color: C.orange, fontWeight: 600 }}>{fmtPct(mdd)}</span>
                </div>
                <div style={{ height: 5, borderRadius: 3, background: C.barTrack, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: mddBar, background: 'linear-gradient(90deg,#F4A93C,#FF8A4C)', borderRadius: 3 }} />
                </div>
              </div>

              {/* Vol bar */}
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 5 }}>
                  <span style={{ color: C.textMuted }}>{t.volatilityLabel}</span>
                  <span style={{ fontFamily: FONT.mono, color: C.orange, fontWeight: 600 }}>{fmtPct(vol)}</span>
                </div>
                <div style={{ height: 5, borderRadius: 3, background: C.barTrack, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: volBar, background: 'linear-gradient(90deg,#F4A93C,#FF8A4C)', borderRadius: 3 }} />
                </div>
              </div>
            </>
          )}

          {/* Excess return badge */}
          <span style={{
            fontFamily: FONT.mono, fontSize: 11, color: C.blueSoft,
            background: 'rgba(62,123,250,0.1)', border: '1px solid rgba(62,123,250,0.2)',
            padding: '3px 7px', borderRadius: 7, flexShrink: 0, whiteSpace: 'nowrap',
          }}>
            vs {fmtPct(excess)}
          </span>
        </div>

        {/* halt_resumption 설명 — 카드 하단 인라인 확장(플로팅 아님, overflow:hidden 대응) */}
        {haltInfoOpen && item.halt_resumption === true && (
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              marginTop: 12, padding: '10px 12px', borderRadius: 10,
              background: C.barTrack, border: `1px solid ${C.cardBorderDefault}`,
              fontSize: 11.5, lineHeight: 1.5, color: C.textPrimary, fontWeight: 400,
            }}
          >
            {t.haltResumptionTitle}
          </div>
        )}
      </button>

      {/* Backtest panel */}
      {open && (
        <BacktestPanel
          status={btDetail.status}
          detail={btDetail.detail}
          market={market}
          days={days}
          lang={lang}
          t={t}
          hasNews={item.has_news === true}
          newsStatus={newsDetail.status}
          newsArticles={newsDetail.articles}
        />
      )}
    </div>
  )
}
