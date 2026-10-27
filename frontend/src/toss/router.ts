import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Environment, Screen, graniteEvent } from '@apps-in-toss/web-framework'
import { parseEntry, parseHash, routeToHash, type Route } from './routes'

/**
 * history 기반 라우터. 앱 안에서 몇 번째 화면인지(idx)를 history.state에 적어 둔다.
 *
 * 뒤로가기: SDK 내비게이션 바 버튼과 안드로이드 시스템 백버튼은 graniteEvent backEvent로 들어온다.
 * 핸들러를 등록하면 기본 동작이 막히므로(문서), 여기서 직접 정한다 —
 * 앱 안에 이전 화면이 있으면(idx > 0) history.back(), 첫 화면이면 미니앱 종료(Screen.close).
 * 공유 링크로 상세에 바로 들어온 경우도 상세가 첫 화면이므로 뒤로가기 = 종료다.
 */

interface HistoryState {
  idx: number
  scrollY?: number
}

function currentState(): HistoryState {
  const s = window.history.state as Partial<HistoryState> | null
  return { idx: typeof s?.idx === 'number' ? s.idx : 0, scrollY: s?.scrollY }
}

function readInitialURL(): string {
  try {
    return Environment.initialURL ?? ''
  } catch {
    return ''
  }
}

export interface Router {
  route: Route
  /** 앱 안에서 몇 번째 화면인지. 0이면 뒤로가기 시 미니앱이 닫힌다. */
  depth: number
  /** 이 화면을 떠날 때 저장해 둔 스크롤 위치(뒤로가기로 돌아온 경우). */
  restoreScrollY: number | undefined
  push: (route: Route) => void
  replace: (route: Route) => void
  back: () => void
}

export function useHistoryRouter(): Router {
  const [entry] = useState(() => {
    const route = parseEntry(readInitialURL(), window.location)
    // 새로고침이면 기존 idx를 유지하고, 첫 진입이면 0으로 시작한다.
    const state = parseHash(window.location.hash) ? currentState() : { idx: 0 }
    window.history.replaceState(state, '', routeToHash(route))
    return { route, state }
  })
  const [route, setRoute] = useState<Route>(entry.route)
  const [state, setState] = useState<HistoryState>(entry.state)

  useEffect(() => {
    const onPop = () => {
      setRoute(parseHash(window.location.hash) ?? entry.route)
      setState(currentState())
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [entry.route])

  const back = useCallback(() => {
    if (currentState().idx > 0) {
      window.history.back()
      return
    }
    Screen.close().catch((e: unknown) => console.error('[router] 미니앱 종료 실패', e))
  }, [])

  useEffect(() => {
    try {
      return graniteEvent.addEventListener('backEvent', {
        onEvent: back,
        onError: (e) => console.error('[router] backEvent 오류', e),
      })
    } catch (e) {
      // 브리지가 없는 환경(구버전 등) — 기본 뒤로가기 동작에 맡긴다.
      console.error('[router] backEvent 구독 실패', e)
      return undefined
    }
  }, [back])

  const push = useCallback((next: Route) => {
    const cur = currentState()
    // 돌아왔을 때 복원할 수 있게 떠나는 화면의 스크롤 위치를 남긴다.
    window.history.replaceState({ ...cur, scrollY: window.scrollY }, '', window.location.hash)
    const nextState: HistoryState = { idx: cur.idx + 1 }
    window.history.pushState(nextState, '', routeToHash(next))
    setRoute(next)
    setState(nextState)
    window.scrollTo(0, 0)
  }, [])

  const replace = useCallback((next: Route) => {
    window.history.replaceState(currentState(), '', routeToHash(next))
    setRoute(next)
  }, [])

  return { route, depth: state.idx, restoreScrollY: state.scrollY, push, replace, back }
}

const RouterContext = createContext<Router | null>(null)
export const RouterProvider = RouterContext.Provider

export function useRouter(): Router {
  const r = useContext(RouterContext)
  if (!r) throw new Error('useRouter는 RouterProvider 안에서만 쓸 수 있어요')
  return r
}

/** 스크롤 복원 — 콘텐츠가 그려진 뒤(ready) 한 번만 적용한다. */
export function useRestoreScroll(ready: boolean): void {
  const { restoreScrollY } = useRouter()
  const [done, setDone] = useState(false)
  useEffect(() => {
    if (!ready || done) return
    setDone(true)
    if (restoreScrollY) window.scrollTo(0, restoreScrollY)
  }, [ready, done, restoreScrollY])
}
