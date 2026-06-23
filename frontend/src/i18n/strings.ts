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
}

const STR: Record<Lang, Strings> = {
  ko: {
    tagline:       '이미 오른 것들의 명예의 전당',
    disclaimer:    '투자 조언 아님 · FomoBot은 지나간 걸 보여줄 뿐이에요',
    moveLabel:     '기간 상승',
    volatilityLabel: '변동성 σ',
    btTitle:       '그때 샀다면?',
    btReturn:      '지금 수익률',
    btPath:        '가는 길 최저점',
    buyPre:        '',
    buySuf:        '일 전 매수',
    profitQuip:    '안 샀죠? 그럴 줄 알았어요.',
    lossQuip:      '안 사길 잘했네요, 이번만큼은.',
    loading:       '급등주 줄 세우는 중…',
    loadingSub:    'FomoBot이 후회 거리를 계산하고 있어요',
    empty:         '조건에 맞는 급등주가 없어요',
    emptySub:      '시장이 평화롭네요. (지루하다는 뜻이에요)',
    emptyBtn:      '기간 바꾸기',
    errorTitle:    '데이터를 못 불러왔어요',
    errorSub:      'FomoBot이 잠깐 한눈팔았나 봐요.',
    retry:         '다시 시도',
    noBacktest:    '백테스트 데이터 없음',
    btLoading:     '계산 중…',
  },
  en: {
    tagline:       'Hall of fame for things that already mooned',
    disclaimer:    'Not financial advice · FomoBot just shows what you missed',
    moveLabel:     'period gain',
    volatilityLabel: 'vol σ',
    btTitle:       'If you had bought back then?',
    btReturn:      'Return now',
    btPath:        'Worst dip on the way',
    buyPre:        'Bought ',
    buySuf:        'd ago',
    profitQuip:    "Didn't buy, did you? Figures.",
    lossQuip:      'Good thing you skipped it — this once.',
    loading:       'Lining up the movers…',
    loadingSub:    'FomoBot is calculating your regrets',
    empty:         'No movers match your filter',
    emptySub:      'Market is calm. (read: boring)',
    emptyBtn:      'Change period',
    errorTitle:    "Couldn't load the data",
    errorSub:      'FomoBot looked away for a second.',
    retry:         'Retry',
    noBacktest:    'No backtest data',
    btLoading:     'Calculating…',
  },
}

export function useStrings(lang: Lang): Strings {
  return STR[lang]
}
