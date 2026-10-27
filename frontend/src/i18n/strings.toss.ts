import { SHARED_KO, type CommonStrings } from './strings'

/**
 * 토스 미니앱 문구(한국어 고정). "단순 시세 조회" 범위에 맞춰 매수 시점·후회·FOMO를
 * 연상시키는 표현을 쓰지 않는다. 웹과 글자가 같은 문구는 SHARED_KO에서 가져온다.
 */
export const TOSS_STR: CommonStrings = {
  ...SHARED_KO,
  disclaimer: '투자 권유가 아니에요. 지난 시세를 보여드려요',
  loading: '순위를 불러오는 중이에요…',
  loadingSub: '잠시만 기다려 주세요',
  emptySub: '다른 기간이나 시장을 선택해 보세요',
  errorSub: '잠시 후 다시 시도해 주세요',
  breadthPanic: '하락 종목이 더 많아요',
  breadthFomo: '상승 종목이 더 많아요',
  breadthNeutral: '상승과 하락이 비슷해요',
}

/** 토스 전용 화면(검색·상세·공유) 문구. 웹과 공유하지 않으므로 CommonStrings 밖에 둔다. */
export const TOSS_UI = {
  searchPlaceholder: '종목명 또는 코드로 검색',
  searchHint: '종목명이나 코드를 입력해 주세요',
  searching: '찾고 있어요…',
  searchEmpty: '찾는 종목이 없어요',
  searchEmptySub: '종목명이나 코드를 다시 확인해 주세요',
  share: '공유하기',
  shareFailed: '공유하지 못했어요. 잠시 후 다시 시도해 주세요',
  prevDay: '전일 대비',
  periodChanges: '기간별 등락률',
  sinceListing: (d: string) => `상장 후 · ${d}부터`,
  lastTraded: (d: string) => `마지막 거래일 ${d}`,
  delisted: '상장폐지',
  chartHigh: '최고',
  chartLow: '최저',
  correctingTitle: '데이터를 정리하고 있어요',
  correctingSub: '정리가 끝나면 시세를 다시 보여드릴게요',
  noDataTitle: '시세 정보가 없어요',
  noDataSub: '이 종목은 보여드릴 시세가 없어요',
  notFoundTitle: '종목을 찾을 수 없어요',
  notFoundSub: '링크가 올바른지 확인해 주세요',
  allRankings: '전체 순위 보기',
  stockShareMessage: (name: string) => `${name} 시세`,
  rankingsShareMessage: (market: string, period: string, order: string) => `${market} ${period} ${order} 순위`,
  orderShort: { desc: '상승률', asc: '하락률' },
  // 이용권은 전면광고만 건너뛴다(배너는 그대로) — 부제에서 범위를 분명히 한다.
  adFreeCta: '광고 보고 24시간 광고 없이 쓰기',
  adFreeSub: '종목을 열 때 나오는 전체 화면 광고가 사라져요',
  adFreePreparing: '광고를 준비하고 있어요',
  adFreeActive: '전체 화면 광고 없이 쓰는 중이에요',
  adFreeRemaining: (h: number, m: number) => (h > 0 ? `${h}시간 ${m}분 남았어요` : `${m}분 남았어요`),
} as const
