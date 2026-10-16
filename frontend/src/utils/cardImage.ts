import type { ShareParams } from '../../shared/share'

/** 공유 랜딩 "이미지 저장" — 저장 방식 결정과 파일명. DOM에 의존하지 않는 순수 함수만 둔다. */

export type SaveMode =
  | 'share-file'   // navigator.share({ files }) — 모바일 공유 시트에서 사진 저장
  | 'download'     // blob URL + <a download>
  | 'long-press'   // 버튼 대신 "이미지를 길게 눌러 저장하세요" 안내

export function cardFileName(p: ShareParams): string {
  return `fomobot-${p.ticker}-${p.from}_${p.to}.png`
}

/** 카카오톡 인앱 브라우저 — 파일 공유도 다운로드도 막혀 있어 길게 누르기만 동작한다. */
export function isKakaoInApp(userAgent: string): boolean {
  return /KAKAOTALK/i.test(userAgent)
}

export function decideSaveMode(opts: {
  /** 페이지 로드 때 카드 PNG를 blob으로 받았는가 */
  hasBlob: boolean
  userAgent: string
  /** navigator.canShare?.({ files: [file] }) 결과 */
  canShareFiles: boolean
}): SaveMode {
  if (!opts.hasBlob || isKakaoInApp(opts.userAgent)) return 'long-press'
  return opts.canShareFiles ? 'share-file' : 'download'
}
