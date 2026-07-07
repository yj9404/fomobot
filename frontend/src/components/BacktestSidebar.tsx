import { useC } from '../ThemeContext'
import { FONT } from '../tokens'
import { BacktestPanel } from './BacktestPanel'
import type { RankingItem, Market, Lang, BacktestDetailResponse } from '../types'
import type { Strings } from '../i18n/strings'

interface BtDetailEntry {
  status: 'idle' | 'loading' | 'ok' | 'error'
  detail: BacktestDetailResponse | null
}

interface Props {
  selected: RankingItem | null
  btDetail: BtDetailEntry
  market: Market
  days: number
  lang: Lang
  t: Strings
}

export function BacktestSidebar({ selected, btDetail, market, days, lang, t }: Props) {
  const C = useC()

  return (
    <div style={{
      width: 320,
      flexShrink: 0,
      background: C.surfaceBt,
      borderLeft: `1px solid ${C.borderSub}`,
      display: 'flex',
      flexDirection: 'column',
      position: 'sticky',
      top: 0,
      height: '100vh',
      overflowY: 'auto',
      scrollbarWidth: 'thin',
      fontFamily: FONT.sans,
    }}>
      {!selected ? (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 10,
          padding: 28,
          textAlign: 'center',
        }}>
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" style={{ opacity: 0.25 }}>
            <rect x="4" y="26" width="6" height="10" rx="2" fill={C.blue} />
            <rect x="14" y="18" width="6" height="18" rx="2" fill={C.blue} />
            <rect x="24" y="10" width="6" height="26" rx="2" fill={C.blue} />
            <rect x="34" y="4" width="6" height="32" rx="2" fill={C.blue} />
          </svg>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.textMuted }}>
            {lang === 'ko' ? '항목을 선택하세요' : 'Select an item'}
          </div>
          <div style={{ fontSize: 12, color: C.textDim, lineHeight: 1.6 }}>
            {lang === 'ko'
              ? '테이블에서 행을 클릭하면\n백테스트 결과가 여기에 표시됩니다'
              : 'Click a row in the table\nto see backtest results here'}
          </div>
        </div>
      ) : (
        <>
          {/* Selected stock header */}
          <div style={{
            padding: '20px 18px 16px',
            borderBottom: `1px solid ${C.borderSub}`,
            background: C.surface,
          }}>
            <div style={{ fontSize: 11, color: C.textDim, marginBottom: 5, letterSpacing: '0.05em', textTransform: 'uppercase', fontWeight: 600 }}>
              {lang === 'ko' ? '선택된 종목' : 'Selected'}
            </div>
            <div style={{ fontSize: 19, fontWeight: 800, color: C.textPrimary, letterSpacing: '-0.02em' }}>
              {selected.name ?? selected.ticker}
            </div>
            <div style={{ fontFamily: FONT.mono, fontSize: 12, color: C.textDim, marginTop: 3 }}>
              {selected.ticker}
            </div>
          </div>

          <BacktestPanel
            status={btDetail.status}
            detail={btDetail.detail}
            market={market}
            days={days}
            lang={lang}
            t={t}
          />
        </>
      )}
    </div>
  )
}
