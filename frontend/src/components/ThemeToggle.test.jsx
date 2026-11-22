import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ThemeToggle from './ThemeToggle.jsx'

function stubMatchMedia(matches) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('по умолчанию включает светлую тему и переключает на тёмную', async () => {
    stubMatchMedia(false)
    const user = userEvent.setup()
    render(<ThemeToggle />)

    const button = screen.getByRole('button', { name: 'Включить тёмную тему' })
    await waitFor(() =>
      expect(document.documentElement.dataset.theme).toBe('light'),
    )
    expect(localStorage.getItem('theme')).toBe('light')

    await user.click(button)

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(
      screen.getByRole('button', { name: 'Включить светлую тему' }),
    ).toBeInTheDocument()
  })

  it('учитывает сохранённую тёмную тему', async () => {
    stubMatchMedia(false)
    localStorage.setItem('theme', 'dark')
    render(<ThemeToggle />)

    await waitFor(() =>
      expect(document.documentElement.dataset.theme).toBe('dark'),
    )
    expect(
      screen.getByRole('button', { name: 'Включить светлую тему' }),
    ).toBeInTheDocument()
  })

  it('использует системную тему, если сохранённой нет', async () => {
    stubMatchMedia(true)
    render(<ThemeToggle />)

    await waitFor(() =>
      expect(document.documentElement.dataset.theme).toBe('dark'),
    )
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('добавляет класс floating для плавающей кнопки', () => {
    render(<ThemeToggle floating />)
    expect(screen.getByRole('button')).toHaveClass('theme-toggle-floating')
  })
})
