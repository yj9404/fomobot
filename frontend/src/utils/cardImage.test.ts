import { describe, expect, it } from 'vitest'
import { cardFileName, decideSaveMode, isKakaoInApp, isMobileDevice } from './cardImage'

const UA = {
  kakaoAndroid: 'Mozilla/5.0 (Linux; Android 14; SM-S918N Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/141.0.0.0 Mobile Safari/537.36 KAKAOTALK/25.8.2',
  kakaoIos: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 KAKAOTALK 25.8.2',
  androidChrome: 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
  iosSafari: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Mobile/15E148 Safari/604.1',
  windowsChrome: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
  // iPadOS Safari는 데스크톱 UA를 쓴다
  mac: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15',
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

describe('isMobileDevice', () => {
  it('Android·iPhone은 모바일, Windows·맥은 데스크톱', () => {
    expect(isMobileDevice(UA.androidChrome, 5)).toBe(true)
    expect(isMobileDevice(UA.iosSafari, 5)).toBe(true)
    expect(isMobileDevice(UA.windowsChrome, 10)).toBe(false)  // 터치 노트북도 데스크톱
    expect(isMobileDevice(UA.mac, 0)).toBe(false)
  })

  it('맥 UA + 터치 포인트 = iPadOS', () => {
    expect(isMobileDevice(UA.mac, 5)).toBe(true)
  })
})

describe('decideSaveMode', () => {
  const m = (userAgent: string, canShareFiles: boolean, maxTouchPoints = 5, hasBlob = true) =>
    decideSaveMode({ hasBlob, userAgent, maxTouchPoints, canShareFiles })

  it('모바일 + 파일 공유 가능 → share-file', () => {
    expect(m(UA.iosSafari, true)).toBe('share-file')
    expect(m(UA.androidChrome, true)).toBe('share-file')
    expect(m(UA.mac, true, 5)).toBe('share-file')  // iPadOS
  })

  it('모바일 + 파일 공유 불가 → download', () => {
    expect(m(UA.androidChrome, false)).toBe('download')
  })

  it('데스크톱은 파일 공유를 지원해도 download', () => {
    expect(m(UA.windowsChrome, true, 0)).toBe('download')
    expect(m(UA.windowsChrome, false, 0)).toBe('download')
    expect(m(UA.mac, true, 0)).toBe('download')
  })

  it('카카오톡 인앱은 canShare 결과와 무관하게 long-press', () => {
    expect(m(UA.kakaoAndroid, true)).toBe('long-press')
    expect(m(UA.kakaoIos, false)).toBe('long-press')
  })

  it('blob을 못 받았으면 long-press', () => {
    expect(m(UA.androidChrome, true, 5, false)).toBe('long-press')
    expect(m(UA.windowsChrome, true, 0, false)).toBe('long-press')
  })
})
