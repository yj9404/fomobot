import type { ShareParams } from '../../shared/share'

/** 공유 랜딩 "이미지 저장" — 저장 방식 결정과 파일명. DOM에 의존하지 않는 순수 함수만 둔다. */

export type SaveMode =
  | 'share-file'   // navigator.share({ files }) — 모바일 공유 시트에서 사진 저장
  | 'download'     // blob URL + <a download> — 데스크톱은 항상 이쪽
  | 'long-press'   // 버튼 대신 "이미지를 길게 눌러 저장하세요" 안내

export function cardFileName(p: ShareParams): string {
  return `fomobot-${p.ticker}-${p.from}_${p.to}.png`
}

/** 카카오톡 인앱 브라우저 — 파일 공유도 다운로드도 막혀 있어 길게 누르기만 동작한다. */
export function isKakaoInApp(userAgent: string): boolean {
  return /KAKAOTALK/i.test(userAgent)
}

/**
 * 휴대폰·태블릿인가. iPadOS는 데스크톱(Macintosh) UA를 쓰므로 터치 포인트로 구분한다.
 * Windows 터치 노트북은 데스크톱으로 본다.
 */
export function isMobileDevice(userAgent: string, maxTouchPoints: number): boolean {
  if (/Android|iPhone|iPad|iPod/i.test(userAgent)) return true
  return /Macintosh/.test(userAgent) && maxTouchPoints > 1
}

export function decideSaveMode(opts: {
  /** 페이지 로드 때 카드 PNG를 blob으로 받았는가 */
  hasBlob: boolean
  userAgent: string
  /** navigator.maxTouchPoints — iPadOS 판별용 */
  maxTouchPoints: number
  /** navigator.canShare?.({ files: [file] }) 결과 */
  canShareFiles: boolean
}): SaveMode {
  if (!opts.hasBlob || isKakaoInApp(opts.userAgent)) return 'long-press'
  // 데스크톱은 파일 공유를 지원해도(Windows Chrome 등) 공유창 대신 바로 다운로드한다 —
  // "이미지 저장" 버튼에서 공유창이 뜨면 기대와 다르다.
  if (!isMobileDevice(opts.userAgent, opts.maxTouchPoints)) return 'download'
  return opts.canShareFiles ? 'share-file' : 'download'
}
