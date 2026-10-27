import { displayStockName } from '../format'

interface Searchable {
  ticker: string
  name: string | null
}

/**
 * 검색 결과 재정렬(토스 전용 — 공용 검색 API의 정렬은 웹과 같이 쓰므로 바꾸지 않는다).
 * 이름 완전 일치 > 이름 접두 일치 > 티커 접두 일치 > 나머지.
 * 같은 그룹 안에서는 받은 순서를 유지한다(검색 응답에 시총이 없어 그 외 기준이 없다).
 * 이름은 원래 이름과 화면 표시 이름("… Common Stock" 꼬리 제거) 둘 다로 비교한다.
 */
export function rankSearchResults<T extends Searchable>(items: T[], query: string): T[] {
  const q = query.trim().toLowerCase()
  if (!q) return items

  const group = (item: T): number => {
    const names = item.name ? [item.name, displayStockName(item.name)].map((n) => n.toLowerCase()) : []
    if (names.some((n) => n === q)) return 0
    if (names.some((n) => n.startsWith(q))) return 1
    if (item.ticker.toLowerCase().startsWith(q)) return 2
    return 3
  }

  return items
    .map((item, i) => ({ item, i, g: group(item) }))
    .sort((a, b) => a.g - b.g || a.i - b.i)
    .map((x) => x.item)
}
