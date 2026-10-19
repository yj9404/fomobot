import { createContext, useContext, useState, useMemo, useLayoutEffect, useCallback, type ReactNode } from 'react'
import { DARK, LIGHT, DARK_DECLINE_OVERRIDE, LIGHT_DECLINE_OVERRIDE } from './tokens'
import type { Colors, Theme } from './tokens'

type AtmosphereMode = 'rise' | 'fall'

interface ThemeCtx {
  theme: Theme
  C: Colors
  toggle: () => void
  atmosphereMode: AtmosphereMode
  setAtmosphereMode: (m: AtmosphereMode) => void
}

const Ctx = createContext<ThemeCtx>({
  theme: 'light',
  C: LIGHT,
  toggle: () => {},
  atmosphereMode: 'rise',
  setAtmosphereMode: () => {},
})

/** fixedTheme을 주면 저장값과 토글을 무시하고 그 테마로 고정한다(토스 미니앱은 라이트 전용). */
export function ThemeProvider({ children, fixedTheme }: { children: ReactNode; fixedTheme?: Theme }) {
  const [storedTheme, setTheme] = useState<Theme>(() => {
    if (fixedTheme) return fixedTheme
    try { return (localStorage.getItem('fomobot-theme') as Theme) ?? 'light' } catch { return 'light' }
  })
  const theme = fixedTheme ?? storedTheme
  const [atmosphereMode, setAtmosphereMode] = useState<AtmosphereMode>('rise')

  const C = useMemo<Colors>(() => {
    const base = theme === 'dark' ? DARK : LIGHT
    if (atmosphereMode === 'rise') return base
    const override = theme === 'dark' ? DARK_DECLINE_OVERRIDE : LIGHT_DECLINE_OVERRIDE
    return { ...base, ...override } as Colors
  }, [theme, atmosphereMode])

  useLayoutEffect(() => {
    document.body.style.background = C.bg
    document.body.style.transition = 'background-color 0.25s ease'
  }, [C.bg])

  const toggle = useCallback(() => {
    if (fixedTheme) return
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    try { localStorage.setItem('fomobot-theme', next) } catch {}
    setTheme(next)
  }, [theme, fixedTheme])

  return (
    <Ctx.Provider value={{ theme, C, toggle, atmosphereMode, setAtmosphereMode }}>
      {children}
    </Ctx.Provider>
  )
}

export function useTheme() { return useContext(Ctx) }
export function useC(): Colors { return useContext(Ctx).C }
