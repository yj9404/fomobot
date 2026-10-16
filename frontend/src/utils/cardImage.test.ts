import { describe, expect, it } from 'vitest'
import { cardFileName, decideSaveMode, isKakaoInApp } from './cardImage'

const UA = {
  kakaoAndroid: 'Mozilla/5.0 (Linux; Android 14; SM-S918N Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/141.0.0.0 Mobile Safari/537.36 KAKAOTALK/25.8.2',
  kakaoIos: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KAKAOTALK 25.8.2',
  androidChrome: 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
  iosSafari: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1',
  windowsChrome: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
}

describe('cardFileName', () => {
  it('fomobot-{ticker}-{from}_{to}.png', () => {
    expect(cardFileName({ market: 'kospi', ticker: '005930', from: '2025-10-15', to: '2026-10-15' }))
      .toBe('fomobot-005930-2025-10-15_2026-10-15.png')
  })
})

describe('isKakaoInApp', () => {
  it('카카오톡 인앱(Android/iOS)만 true', () => {
    expect(isKakaoInApp(UA.kakaoAndroid)).toBe(true)
    expect(isKakaoInApp(UA.kakaoIos)).toBe(true)
    expect(isKakaoInApp(UA.androidChrome)).toBe(false)
    expect(isKakaoInApp(UA.iosSafari)).toBe(false)
  })
})

describe('decideSaveMode', () => {
  it('파일 공유 가능 → share-file', () => {
    expect(decideSaveMode({ hasBlob: true, userAgent: UA.iosSafari, canShareFiles: true })).toBe('share-file')
    expect(decideSaveMode({ hasBlob: true, userAgent: UA.androidChrome, canShareFiles: true })).toBe('share-file')
  })

  it('파일 공유 불가 → download', () => {
    expect(decideSaveMode({ hasBlob: true, userAgent: UA.windowsChrome, canShareFiles: false })).toBe('download')
  })

  it('카카오톡 인앱은 canShare 결과와 무관하게 long-press', () => {
    expect(decideSaveMode({ hasBlob: true, userAgent: UA.kakaoAndroid, canShareFiles: true })).toBe('long-press')
    expect(decideSaveMode({ hasBlob: true, userAgent: UA.kakaoIos, canShareFiles: false })).toBe('long-press')
  })

  it('blob을 못 받았으면 long-press', () => {
    expect(decideSaveMode({ hasBlob: false, userAgent: UA.androidChrome, canShareFiles: true })).toBe('long-press')
  })
})
