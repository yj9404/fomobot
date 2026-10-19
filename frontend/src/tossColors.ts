// 국내(토스증권 등) 시세 화면의 관례: 상승 빨강, 하락 파랑. 웹은 테마의 green/red를 그대로 쓴다.
// 값은 TDS 색상 토큰과 같다: @toss/tds-colors 0.1.0의 red500(라이트) #f04452, blue500(라이트) #3182f6.
// 상승/하락 전용 시맨틱 토큰은 패키지에 없어서 red/blue 500을 직접 가리킨다.
export const KR_UP = '#F04452'
export const KR_DOWN = '#3182F6'

export function changeColor(pct: number, neutral: string): string {
  if (pct > 0) return KR_UP
  if (pct < 0) return KR_DOWN
  return neutral
}
