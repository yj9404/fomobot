import { useState, useEffect } from 'react'
import { fetchBreadth } from '../api/breadth'
import type { BreadthResponse, Market } from '../types'

/**
 * data가 null이면 "위젯을 숨긴다"는 뜻이다 — 데이터 없음(404)과 조회 실패를
 * 구분하지 않는다. breadth는 랭킹 페이지의 보조 위젯이라 에러 문구/스켈레톤을
 * 보여줄 가치가 없고, 그냥 안 보이는 편이 낫다(요구사항: 빈 상태 = 완전히 숨김).
 */
export function useBreadth(market: Market): BreadthResponse | null {
  const [data, setData] = useState<BreadthResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    setData(null) // 시장 전환 시 이전 시장 값이 잠깐이라도 보이지 않도록 즉시 초기화

    fetchBreadth(market)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        console.error('[useBreadth]', err)
        setData(null)
      })

    return () => { cancelled = true }
  }, [market])

  return data
}
