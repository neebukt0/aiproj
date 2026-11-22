import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../contexts/AuthContext'
import ProtectedRoute from './ProtectedRoute.jsx'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

function renderRoute({ user = null, loading = false, roles, initial = '/private' }) {
  useAuth.mockReturnValue({ user, loading })

  return render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route path="/login" element={<div>страница входа</div>} />
        <Route path="/" element={<div>главная</div>} />
        <Route
          path="/private"
          element={
            <ProtectedRoute roles={roles}>
              <div>закрытый контент</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('показывает загрузку, пока восстанавливается сессия', () => {
    renderRoute({ loading: true })
    expect(screen.getByText('Загрузка...')).toBeInTheDocument()
    expect(screen.queryByText('закрытый контент')).not.toBeInTheDocument()
  })

  it('перенаправляет неавторизованного пользователя на /login', () => {
    renderRoute({})
    expect(screen.getByText('страница входа')).toBeInTheDocument()
  })

  it('не пускает пользователя с неподходящей ролью', () => {
    renderRoute({ user: { role: 'client' }, roles: ['employee', 'admin'] })
    expect(screen.getByText('главная')).toBeInTheDocument()
    expect(screen.queryByText('закрытый контент')).not.toBeInTheDocument()
  })

  it('пускает пользователя с разрешённой ролью', () => {
    renderRoute({ user: { role: 'admin' }, roles: ['employee', 'admin'] })
    expect(screen.getByText('закрытый контент')).toBeInTheDocument()
  })

  it('пускает любого авторизованного пользователя без ограничения ролей', () => {
    renderRoute({ user: { role: 'client' } })
    expect(screen.getByText('закрытый контент')).toBeInTheDocument()
  })
})
