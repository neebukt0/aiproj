import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

// jsdom не реализует matchMedia — задаём детерминированное значение по умолчанию.
// Отдельные тесты могут переопределить window.matchMedia перед рендером.
function createMatchMedia(matches = false) {
  return vi.fn().mockImplementation((query) => ({
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

beforeEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  window.matchMedia = createMatchMedia(false)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  localStorage.clear()
})
