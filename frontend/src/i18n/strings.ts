import type { RankingItem } from '../types'
import type { WebStrings } from './strings.web'

/**
 * 웹과 토스 빌드가 함께 쓰는 문구. 토스 번들은 이 파일만 import하고
 * strings.web.ts(백테스트·매수·공유·글 문구)는 import하지 않는다 — 가드 스크립트가 그걸 확인한다.
 */
export interface CommonStrings {
  disclaimer: string
  moveLabel: string
  loading: string
  loadingSub: string
  empty: string
  emptySub: string
  emptyBtn: string
  errorTitle: string
  errorSub: string
  retry: string
  orderRise: string
  orderFall: string
  asOfLabel: string
  haltResumptionTitle: string
  startValidityGapTitle: (date: string) => string
  startValidityHaltedTitle: (date: string) => string
  breadthUp: string
  breadthDown: string
  breadthFlat: string
  breadthPanic: string
  breadthFomo: string
  breadthNeutral: string
}

/** 웹 컴포넌트가 받는 전체 문구 = 공통 + 웹 전용. */
export type Strings = CommonStrings & WebStrings

/** 웹(ko)과 토스가 글자까지 똑같은 한국어 문구. 어긋나지 않게 한 곳에 둔다. */
export const SHARED_KO = {
  moveLabel: '기간 등락',
  empty: '조건에 맞는 항목이 없어요',
  emptyBtn: '필터 초기화',
  errorTitle: '데이터를 못 불러왔어요',
  retry: '다시 시도',
  orderRise: '상승률 상위 ▲',
  orderFall: '하락률 상위 ▼',
  asOfLabel: '기준일',
  haltResumptionTitle: '이 종목은 장기 거래정지 후 재개된 첫날입니다. 재개 첫날은 가격제한폭(±30%)이 적용되지 않아 하루 등락이 클 수 있습니다.',
  startValidityGapTitle: (d: string) => `이 기간 시작 시점에는 거래 데이터가 없습니다. 실제 비교 시작일: ${d}`,
  startValidityHaltedTitle: (d: string) => `이 기간 시작 시점에 거래가 정지 상태였습니다. 실제 비교 시작일: ${d}`,
  breadthUp: '상승',
  breadthDown: '하락',
  breadthFlat: '보합',
} as const

/**
 * 랭킹 카드/행에 ⓘ 아이콘으로 보여줄 문구를 결정한다. halt_resumption과
 * start_validity는 백엔드에서 1d 한정 상호배타(compute_rankings.py의
 * _lookup_start_validity)지만, 프론트도 방어적으로 halt_resumption을
 * 우선한다 — 이미 더 구체적인 설명이므로. 어느 것도 해당 없으면 null
 * (호출부가 아이콘 자체를 렌더링하지 않아야 함).
 */
export function getInfoBadgeText(item: RankingItem, t: CommonStrings): string | null {
  if (item.halt_resumption === true) return t.haltResumptionTitle
  if (item.start_validity === 'halted' && item.first_valid_date) {
    return t.startValidityHaltedTitle(item.first_valid_date)
  }
  if (item.start_validity === 'gap' && item.first_valid_date) {
    return t.startValidityGapTitle(item.first_valid_date)
  }
  return null
}
