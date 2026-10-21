import type { Lang } from '../types'
import { SHARED_KO, type CommonStrings, type Strings } from './strings'

/** 웹에만 있는 문구 — 백테스트, 매수 시점, 뉴스 등. 토스 번들에 들어가면 안 된다. */
export interface WebStrings {
  tagline: string
  volatilityLabel: string
  btTitle: string
  btReturn: string
  btPath: string
  buyPre: string
  buySuf: string
  profitQuip: string
  lossQuip: string
  noBacktest: string
  btLoading: string
  orderFallCopy: string
  btDcaBadge: string
  btCompareLumpSum: string
  btDeficitWarning: string
  newsTitle: string
  newsLoading: string
  newsDotTitle: string
}

export type { CommonStrings }

const WEB_STR: Record<Lang, Strings> = {
  ko: {
    ...SHARED_KO,
    tagline: '이미 오른 것들의 명예의 전당',
    disclaimer: '투자 조언이 아닙니다. FomoBot은 지나간 걸 보여줄 뿐이에요',
    volatilityLabel: '변동성 σ',
    btTitle: '그때 샀다면?',
    btReturn: '지금 수익률',
    btPath: '가는 길 최저점',
    buyPre: '',
    buySuf: '일 전 매수',
    profitQuip: '안 샀죠? 그럴 줄 알았어요.',
    lossQuip: '안 사길 잘했네요, 이번만큼은.',
    loading: '급등 항목 줄 세우는 중…',
    loadingSub: 'FomoBot이 후회 거리를 계산하고 있어요',
    emptySub: '시장이 평화롭네요. (지루하다는 뜻이에요)',
    errorSub: 'FomoBot이 잠깐 한눈팔았나 봐요.',
    noBacktest: '백테스트 데이터 없음',
    btLoading: '계산 중…',
    orderFallCopy: '안 물려서 다행',
    btDcaBadge: '나눠 담기',
    btCompareLumpSum: '한 번에 샀다면',
    btDeficitWarning: '상장이 늦어서 그때는 살 수도 없었어요. 살 수 있었던 날부터 계산했습니다.',
    newsTitle: '관련 뉴스',
    newsLoading: '뉴스 불러오는 중…',
    newsDotTitle: '관련 뉴스 있음',
    breadthPanic: '다들 도망가는 중입니다',
    breadthFomo: '다들 올라타는 중입니다. 당신 빼고.',
    breadthNeutral: '시장도 갈피를 못 잡는 중',
  },
  en: {
    tagline: 'Hall of fame for things that already mooned',
    disclaimer: 'Not financial advice · FomoBot just shows what you missed',
    moveLabel: 'period chg',
    volatilityLabel: 'vol σ',
    btTitle: 'If you had bought back then?',
    btReturn: 'Return now',
    btPath: 'Worst dip on the way',
    buyPre: 'Bought ',
    buySuf: 'd ago',
    profitQuip: "Didn't buy, did you? Figures.",
    lossQuip: 'Good thing you skipped it — this once.',
    loading: 'Lining up the movers…',
    loadingSub: 'FomoBot is calculating your regrets',
    empty: 'No movers match your filter',
    emptySub: 'Market is calm. (read: boring)',
    emptyBtn: 'Reset filters',
    errorTitle: "Couldn't load the data",
    errorSub: 'FomoBot looked away for a second.',
    retry: 'Retry',
    noBacktest: 'No backtest data',
    btLoading: 'Calculating…',
    orderRise: 'Top Gainers ▲',
    orderFall: 'Top Losers ▼',
    orderFallCopy: 'Glad you skipped these',
    asOfLabel: 'As of',
    closeNote: 'close',
    btDcaBadge: 'DCA',
    btCompareLumpSum: 'If bought all at once',
    btDeficitWarning: "It wasn't even listed yet back then — calculated from the first day you could actually buy it.",
    newsTitle: 'Related news',
    newsLoading: 'Loading news…',
    newsDotTitle: 'Related news available',
    haltResumptionTitle: 'This stock just resumed trading after a long halt. The daily price limit (±30%) doesn\'t apply on the first day back, so a large move here is expected — not a data error.',
    startValidityGapTitle: (d) => `No trading data existed yet at the start of this period. Actual comparison start date: ${d}`,
    startValidityHaltedTitle: (d) => `Trading was suspended at the start of this period. Actual comparison start date: ${d}`,
    breadthUp: 'Up',
    breadthDown: 'Down',
    breadthFlat: 'Flat',
    breadthPanic: "Everyone's running for the exits",
    breadthFomo: "Everyone's piling in. Except you.",
    breadthNeutral: "Even the market can't make up its mind",
  },
}

export function useStrings(lang: Lang): Strings {
  return WEB_STR[lang]
}
