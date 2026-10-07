import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Monitor, Moon, Sun } from 'lucide-react'

export type ThemeMode = 'light' | 'dark' | 'system'
const validMode = (value: unknown): value is ThemeMode => value === 'light' || value === 'dark' || value === 'system'
const ThemeContext = createContext<{ mode: ThemeMode; setMode: (mode: ThemeMode) => void }>({ mode: 'dark', setMode: () => {} })

function applyTheme(mode: ThemeMode) {
  const dark = mode === 'system' ? window.matchMedia('(prefers-color-scheme: dark)').matches : mode === 'dark'
  document.documentElement.dataset.themeMode = mode
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0b101a' : '#eef2f8')
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, updateMode] = useState<ThemeMode>(() => {
    const initial = document.documentElement.dataset.themeMode
    return validMode(initial) ? initial : 'dark'
  })
  function setMode(next: ThemeMode) {
    applyTheme(next); updateMode(next)
    try { localStorage.setItem('quoteflow-theme', next) } catch { /* Keep the choice in memory. */ }
  }
  useEffect(() => {
    applyTheme(mode)
    if (mode !== 'system') return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => applyTheme('system')
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [mode])
  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key !== 'quoteflow-theme' && event.key !== null) return
      const next = validMode(event.newValue) ? event.newValue : 'dark'
      applyTheme(next); updateMode(next)
    }
    window.addEventListener('storage', sync)
    return () => window.removeEventListener('storage', sync)
  }, [])
  return <ThemeContext.Provider value={{ mode, setMode }}>{children}</ThemeContext.Provider>
}

export function ThemeControl() {
  const { mode, setMode } = useContext(ThemeContext)
  const Icon = mode === 'system' ? Monitor : mode === 'light' ? Sun : Moon
  return <div className="theme-control"><Icon size={14} aria-hidden="true" /><label className="sr-only" htmlFor="appearance-mode">Appearance</label><select id="appearance-mode" aria-label="Appearance" value={mode} onChange={(event) => setMode(event.target.value as ThemeMode)}><option value="dark">Dark</option><option value="light">Light</option><option value="system">System</option></select></div>
}
