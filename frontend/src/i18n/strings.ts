import type { Lang } from '../types'

export interface Strings {
  tagline: string
  disclaimer: string
  moveLabel: string
  volatilityLabel: string
  btTitle: string
  btReturn: string
  btPath: string
  buyPre: string
  buySuf: string
  profitQuip: string
  lossQuip: string
  loading: string
  loadingSub: string
  empty: string
  emptySub: string
  emptyBtn: string
  errorTitle: string
  errorSub: string
  retry: string
  noBacktest: string
  btLoading: string
  orderRise: string
  orderFall: string
  orderFallCopy: string
  asOfLabel: string
  btDcaBadge: string
  btCompareLumpSum: string
  btDeficitWarning: string
}

const STR: Record<Lang, Strings> = {
  ko: {
    tagline: '이미 오른 것들의 명예의 전당',
    disclaimer: '투자 조언이 아닙니다. FomoBot은 지나간 걸 보여줄 뿐이에요',
    moveLabel: '기간 등락',
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
    empty: '조건에 맞는 항목이 없어요',
    emptySub: '시장이 평화롭네요. (지루하다는 뜻이에요)',
    emptyBtn: '필터 초기화',
    errorTitle: '데이터를 못 불러왔어요',
    errorSub: 'FomoBot이 잠깐 한눈팔았나 봐요.',
    retry: '다시 시도',
    noBacktest: '백테스트 데이터 없음',
    btLoading: '계산 중…',
    orderRise: '상승률 상위 ▲',
    orderFall: '하락률 상위 ▼',
    orderFallCopy: '안 물려서 다행',
    asOfLabel: '기준일',
    btDcaBadge: '나눠 담기',
    btCompareLumpSum: '한 번에 샀다면',
    btDeficitWarning: '상장이 늦어서 그때는 살 수도 없었어요. 살 수 있었던 날부터 계산했습니다.',
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
    btDcaBadge: 'DCA',
    btCompareLumpSum: 'If bought all at once',
    btDeficitWarning: "It wasn't even listed yet back then — calculated from the first day you could actually buy it.",
  },
}

export function useStrings(lang: Lang): Strings {
  return STR[lang]
}
