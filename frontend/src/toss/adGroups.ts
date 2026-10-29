/**
 * 앱인토스 광고 그룹 ID — 앱 전체에서 이 파일 한 곳에만 둔다.
 * 콘솔 발급값이고 비밀값이 아니다(어차피 클라이언트 번들에 들어간다).
 *
 * dev 서버·테스트(import.meta.env.DEV)는 문서의 테스트 ID를 쓴다 — 개발 중 실제 ID로 테스트하면 정책 위반이다.
 * 실기기 테스트용 번들도 VITE_TOSS_TEST_ADS=1로 빌드하면 테스트 ID를 쓴다(출시 번들은 플래그 없이 빌드).
 * 실제 ID가 빈 문자열이면 그 광고는 요청하지 않고 건너뛴다(기능은 광고 없이 그대로 동작).
 */
const LIVE = {
  banner: 'ait.v2.live.d7d803200c524f97',
  detailInterstitial: 'ait.v2.live.64b380ae405d417a',
  adFreeReward: 'ait.v2.live.86fdde923b364e94',
}

const TEST: typeof LIVE = {
  banner: 'ait-ad-test-banner-id',
  detailInterstitial: 'ait-ad-test-interstitial-id',
  adFreeReward: 'ait-ad-test-rewarded-id',
}

export const AD_GROUP_IDS = import.meta.env.DEV || import.meta.env.VITE_TOSS_TEST_ADS === '1' ? TEST : LIVE
