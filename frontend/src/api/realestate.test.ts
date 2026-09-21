import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchReRankings,
  fetchReRegionSearch,
  fetchReAptSearch,
  fetchReSegments,
  fetchReComplexNews,
} from './realestate'
import { apiFetch } from './client'

vi.mock('./client', () => ({
  apiFetch: vi.fn(),
}))

describe('realestate API client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('fetchReRankings', () => {
    it('calls apiFetch with default params when no optional params provided', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ items: [] } as any)

      const res = await fetchReRankings('1M')

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/rankings', {
        period: '1M',
        top: 20,
        order: 'desc',
      })
      expect(res).toEqual({ items: [] })
    })

    it('calls apiFetch with seg param, ignoring region params', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ items: [] } as any)

      await fetchReRankings('3M', '11', '11680', '대치동', 50, 'gangnam_school', undefined, undefined, 'asc')

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/rankings', {
        period: '3M',
        top: 50,
        order: 'asc',
        seg: 'gangnam_school',
      })
    })

    it('calls apiFetch with region params when seg is not provided', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ items: [] } as any)

      await fetchReRankings('1Y', '11', '11680', '대치동')

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/rankings', {
        period: '1Y',
        top: 20,
        order: 'desc',
        sido: '11',
        gu: '11680',
        dong: '대치동',
      })
    })

    it('calls apiFetch with minPrice and maxPrice', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ items: [] } as any)

      await fetchReRankings('1M', undefined, undefined, undefined, 20, undefined, 10, 20)

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/rankings', {
        period: '1M',
        top: 20,
        order: 'desc',
        min_price: 10,
        max_price: 20,
      })
    })
  })

  describe('fetchReRegionSearch', () => {
    it('calls apiFetch with query param', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ regions: [] } as any)

      const res = await fetchReRegionSearch('강남')

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/regions', { q: '강남' })
      expect(res).toEqual({ regions: [] })
    })
  })

  describe('fetchReAptSearch', () => {
    it('calls apiFetch with q and period params', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ items: [] } as any)

      const res = await fetchReAptSearch('은마', '3M')

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/search', { q: '은마', period: '3M' })
      expect(res).toEqual({ items: [] })
    })

    it('calls apiFetch with all params including gu and dong', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ items: [] } as any)

      await fetchReAptSearch('은마', '3M', '11680', '대치동')

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/search', {
        q: '은마',
        period: '3M',
        gu: '11680',
        dong: '대치동',
      })
    })
  })

  describe('fetchReSegments', () => {
    it('calls apiFetch to get segments', async () => {
      vi.mocked(apiFetch).mockResolvedValueOnce({ segments: [] } as any)

      const res = await fetchReSegments()

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith('/api/realestate/segments', {})
      expect(res).toEqual({ segments: [] })
    })
  })

  describe('fetchReComplexNews', () => {
    it('calls apiFetch with url encoded complex key and unwrap articles', async () => {
      const mockArticles = [{ title: 'News 1' }, { title: 'News 2' }]
      vi.mocked(apiFetch).mockResolvedValueOnce({ articles: mockArticles } as any)

      const complexKey = '은마아파트'
      const res = await fetchReComplexNews(complexKey)

      expect(apiFetch).toHaveBeenCalledTimes(1)
      expect(apiFetch).toHaveBeenCalledWith(`/api/realestate/news/${encodeURIComponent(complexKey)}`, {})
      expect(res).toEqual(mockArticles)
    })
  })
})
