import { useC } from './ThemeContext'
import { FONT } from './tokens'
import { RouterProvider, useHistoryRouter } from './toss/router'
import { RankingsScreen } from './toss/RankingsScreen'
import { SearchScreen } from './toss/SearchScreen'
import { StockScreen } from './toss/StockScreen'

/**
 * 앱인토스 미니앱 셸. 웹의 App.tsx와 별도라 백테스트·웹 공유·부동산·뉴스·외부 광고·글 등
 * 웹 전용 모듈을 import하지 않는다(그래서 번들에서 제외된다).
 *
 * 화면: 순위(첫 화면) → 검색 → 종목 상세. 화면 전환과 뒤로가기는 toss/router.ts가 맡는다.
 * 떠난 화면은 언마운트한다 — 숨긴 채로 두면 보이지 않는 배너가 살아 있어 노출이 왜곡될 수 있다.
 */
export default function TossApp() {
  const C = useC()
  const router = useHistoryRouter()
  const { route } = router

  return (
    <RouterProvider value={router}>
      <div style={{
        width: '100%', minHeight: '100vh', background: C.surface, fontFamily: FONT.sans,
        display: 'flex', flexDirection: 'column',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}>
        {route.name === 'rankings' && <RankingsScreen route={route} />}
        {route.name === 'search' && <SearchScreen key="search" initialQ={route.q} />}
        {route.name === 'stock' && <StockScreen key={`${route.market}:${route.ticker}`} market={route.market} ticker={route.ticker} />}
      </div>
    </RouterProvider>
  )
}
