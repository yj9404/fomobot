// 국내(토스증권 등) 시세 화면의 관례: 상승 빨강, 하락 파랑. 웹은 테마의 green/red를 그대로 쓴다.
// 값은 토스 디자인 시스템의 red/blue 500 계열 — 최종 값은 QR 테스트 때 화면으로 확인한다.
export const KR_UP = '#F04452'
export const KR_DOWN = '#3182F6'

export function changeColor(pct: number, neutral: string): string {
  if (pct > 0) return KR_UP
  if (pct < 0) return KR_DOWN
  return neutral
}
