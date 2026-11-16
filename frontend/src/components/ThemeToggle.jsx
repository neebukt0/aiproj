import { useEffect, useState } from 'react'

const STORAGE_KEY = 'theme'

function getInitialTheme() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export default function ThemeToggle({ floating = false }) {
  const [theme, setTheme] = useState(getInitialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem(STORAGE_KEY, theme)
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#0b1220' : '#f4f6fb')
  }, [theme])

  const nextTheme = theme === 'dark' ? 'light' : 'dark'
  const label =
    nextTheme === 'dark' ? 'Включить тёмную тему' : 'Включить светлую тему'

  return (
    <button
      type="button"
      className={floating ? 'ghost theme-toggle theme-toggle-floating' : 'ghost theme-toggle'}
      onClick={() => setTheme(nextTheme)}
      aria-label={label}
      title={label}
    >
      <span aria-hidden="true">{theme === 'dark' ? '☀️' : '🌙'}</span>
    </button>
  )
}
