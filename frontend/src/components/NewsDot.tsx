import { useC } from '../ThemeContext'
import type { Strings } from '../i18n/strings'

interface Props {
  show: boolean
  t: Strings
}

/**
 * has_news 인디케이터. 항상 동일한 크기의 슬롯을 차지하고 show일 때만
 * 점을 보이게 한다 — 종목명 길이나 뉴스 유무와 무관하게 이름 텍스트가
 * 시작하는 위치가 행마다 들쭉날쭉해지지 않도록 하기 위함(카드/표 공통).
 * 상승/하락 분위기색과 무관한 중립 blue를 써서 다크·라이트, 상승·하락
 * 뷰 어디서나 자연스럽게 보인다.
 */
export function NewsDot({ show, t }: Props) {
  const C = useC()
  return (
    <span
      title={show ? t.newsDotTitle : undefined}
      style={{
        display: 'inline-block',
        width: 7,
        height: 7,
        borderRadius: '50%',
        flexShrink: 0,
        background: show ? C.blueSoft : 'transparent',
      }}
    />
  )
}
