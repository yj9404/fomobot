import { useState, useEffect } from 'react'
import { fetchReSegments } from '../api/realestate'
import type { SegmentItem } from '../types'

export function useReSegments(): SegmentItem[] {
  const [segments, setSegments] = useState<SegmentItem[]>([])
  useEffect(() => {
    fetchReSegments()
      .then((data) => setSegments(data.segments))
      .catch(() => {})
  }, [])
  return segments
}
