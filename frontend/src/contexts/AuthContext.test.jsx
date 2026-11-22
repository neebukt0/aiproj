import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../api/client'
import { AuthProvider, useAuth } from './AuthContext.jsx'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

function Consumer() {
  const { user, loading, login, register, logout } = useAuth()

  return (
    <div>
      <span data-testid="state">
        {loading ? 'loading' : user ? `${user.email}:${user.role}` : 'anon'}
      </span>
      <button onClick={() => login('client@example.com', 'ClientPass123!')}>
        войти
      </button>
      <button onClick={() => register('new@example.com', 'NewPass123!')}>
        зарегистрироваться
      </button>
      <button onClick={logout}>выйти</button>
    </div>
  )
}

function renderProvider() {
  return render(
    <AuthProvider>
      <Consumer />
    </AuthProvider>,
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('без токена сразу завершает загрузку', async () => {
    renderProvider()

    await waitFor(() =>
      expect(screen.getByTestId('state')).toHaveTextContent('anon'),
    )
    expect(api.get).not.toHaveBeenCalled()
  })

  it('восстанавливает сессию по сохранённому access-токену', async () => {
    localStorage.setItem('at', 'access-token')
    api.get.mockResolvedValue({
      data: { email: 'client@example.com', role: 'client' },
    })

    renderProvider()

    expect(await screen.findByText('client@example.com:client')).toBeInTheDocument()
    expect(api.get).toHaveBeenCalledWith('/api/auth/me')
  })

  it('очищает сессию, если токен недействителен', async () => {
    localStorage.setItem('at', 'expired')
    localStorage.setItem('rt', 'refresh')
    api.get.mockRejectedValue(new Error('401'))

    renderProvider()

    await waitFor(() =>
      expect(screen.getByTestId('state')).toHaveTextContent('anon'),
    )
    expect(localStorage.getItem('at')).toBeNull()
    expect(localStorage.getItem('rt')).toBeNull()
  })

  it('логин сохраняет токены и пользователя', async () => {
    api.post.mockResolvedValue({ data: { access: 'a1', refresh: 'r1' } })
    api.get.mockResolvedValue({
      data: { email: 'client@example.com', role: 'client' },
    })
    const user = userEvent.setup()
    renderProvider()

    await waitFor(() =>
      expect(screen.getByTestId('state')).toHaveTextContent('anon'),
    )
    await user.click(screen.getByRole('button', { name: 'войти' }))

    expect(await screen.findByText('client@example.com:client')).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/api/auth/login', {
      email: 'client@example.com',
      password: 'ClientPass123!',
    })
    expect(localStorage.getItem('at')).toBe('a1')
    expect(localStorage.getItem('rt')).toBe('r1')
  })

  it('регистрация сохраняет токены и пользователя', async () => {
    api.post.mockResolvedValue({ data: { access: 'a2', refresh: 'r2' } })
    api.get.mockResolvedValue({
      data: { email: 'new@example.com', role: 'client' },
    })
    const user = userEvent.setup()
    renderProvider()

    await waitFor(() =>
      expect(screen.getByTestId('state')).toHaveTextContent('anon'),
    )
    await user.click(
      screen.getByRole('button', { name: 'зарегистрироваться' }),
    )

    expect(await screen.findByText('new@example.com:client')).toBeInTheDocument()
    expect(localStorage.getItem('at')).toBe('a2')
    expect(localStorage.getItem('rt')).toBe('r2')
  })

  it('логаут отправляет refresh-токен и очищает сессию', async () => {
    localStorage.setItem('at', 'a1')
    localStorage.setItem('rt', 'r1')
    api.get.mockResolvedValue({
      data: { email: 'client@example.com', role: 'client' },
    })
    api.post.mockResolvedValue({ data: { ok: true } })
    const user = userEvent.setup()
    renderProvider()

    await screen.findByText('client@example.com:client')
    await user.click(screen.getByRole('button', { name: 'выйти' }))

    await waitFor(() =>
      expect(screen.getByTestId('state')).toHaveTextContent('anon'),
    )
    expect(api.post).toHaveBeenCalledWith('/api/auth/logout', { refresh: 'r1' })
    expect(localStorage.getItem('at')).toBeNull()
    expect(localStorage.getItem('rt')).toBeNull()
  })

  it('логаут очищает сессию даже при ошибке сервера', async () => {
    localStorage.setItem('at', 'a1')
    localStorage.setItem('rt', 'r1')
    api.get.mockResolvedValue({
      data: { email: 'client@example.com', role: 'client' },
    })
    api.post.mockRejectedValue(new Error('network'))
    const user = userEvent.setup()
    renderProvider()

    await screen.findByText('client@example.com:client')
    await user.click(screen.getByRole('button', { name: 'выйти' }))

    await waitFor(() =>
      expect(screen.getByTestId('state')).toHaveTextContent('anon'),
    )
    expect(localStorage.getItem('at')).toBeNull()
    expect(localStorage.getItem('rt')).toBeNull()
  })
})
