import { createContext, useContext, useState, useLayoutEffect, type ReactNode } from 'react'
import { DARK, LIGHT } from './tokens'
import type { Colors, Theme } from './tokens'

interface ThemeCtx {
  theme: Theme
  C: Colors
  toggle: () => void
}

const Ctx = createContext<ThemeCtx>({ theme: 'light', C: LIGHT, toggle: () => {} })

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    try { return (localStorage.getItem('fomobot-theme') as Theme) ?? 'light' } catch { return 'light' }
  })

  const C = theme === 'dark' ? DARK : LIGHT

  useLayoutEffect(() => {
    document.body.style.background = C.bg
  }, [C.bg])

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    try { localStorage.setItem('fomobot-theme', next) } catch {}
    setTheme(next)
  }

  return <Ctx.Provider value={{ theme, C, toggle }}>{children}</Ctx.Provider>
}

export function useTheme() { return useContext(Ctx) }
export function useC(): Colors { return useContext(Ctx).C }
