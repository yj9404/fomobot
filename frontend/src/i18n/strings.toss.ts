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

/** 토스 화면에서만 쓰는 문구 — 웹과 공유하는 CommonStrings에는 넣지 않는다. */
export const TOSS_COPY = {
  closeNote: '종가 기준',
}
