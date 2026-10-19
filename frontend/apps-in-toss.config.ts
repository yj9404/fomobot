import { defineConfig } from '@apps-in-toss/web-framework/config'

// 앱인토스 미니앱 설정(SDK 3.x). appName은 콘솔에 등록한 값이라 바꾸면 안 된다.
export default defineConfig({
  appName: 'fomobot',
  brand: {
    // TossHeader 등 토스 화면의 강조색(#3E7BFA 계열)과 맞춘다.
    primaryColor: '#3E7BFA',
  },
  // 앱인토스 기본 내비게이션 바를 쓴다. 자체 헤더에는 뒤로가기·로고를 두지 않으므로
  // 뒤로가기(첫 화면에서는 미니앱 종료)와 앱 이름/로고는 SDK 바가 맡는다.
  navigationBar: {
    withBackButton: true,
    withTitle: true,
  },
  permissions: [],
  webBundleDir: 'dist-toss',
})
