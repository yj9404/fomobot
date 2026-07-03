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

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    try { return (localStorage.getItem('fomobot-theme') as Theme) ?? 'light' } catch { return 'light' }
  })
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
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    try { localStorage.setItem('fomobot-theme', next) } catch {}
    setTheme(next)
  }, [theme])

  return (
    <Ctx.Provider value={{ theme, C, toggle, atmosphereMode, setAtmosphereMode }}>
      {children}
    </Ctx.Provider>
  )
}

export function useTheme() { return useContext(Ctx) }
export function useC(): Colors { return useContext(Ctx).C }
