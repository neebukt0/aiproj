import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuth } from '../contexts/AuthContext'
import Login from './Login.jsx'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

function renderLogin(login = vi.fn()) {
  useAuth.mockReturnValue({ login })

  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>каталог открыт</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

async function fillAndSubmit(user) {
  await user.type(screen.getByPlaceholderText('Email'), 'client@example.com')
  await user.type(screen.getByPlaceholderText('Пароль'), 'ClientPass123!')
  await user.click(screen.getByRole('button', { name: 'Войти' }))
}

describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('после успешного входа переходит в каталог', async () => {
    const login = vi.fn().mockResolvedValue({})
    const user = userEvent.setup()
    renderLogin(login)

    await fillAndSubmit(user)

    expect(login).toHaveBeenCalledWith(
      'client@example.com',
      'ClientPass123!',
    )
    expect(await screen.findByText('каталог открыт')).toBeInTheDocument()
  })

  it('показывает сообщение об ошибке входа', async () => {
    const login = vi.fn().mockRejectedValue({
      response: { data: { detail: 'Неверный email или пароль' } },
    })
    const user = userEvent.setup()
    renderLogin(login)

    await fillAndSubmit(user)

    expect(
      await screen.findByText('Неверный email или пароль'),
    ).toBeInTheDocument()
    expect(screen.queryByText('каталог открыт')).not.toBeInTheDocument()
  })

  it('показывает общую ошибку, если сервер не вернул detail', async () => {
    const login = vi.fn().mockRejectedValue(new Error('network'))
    const user = userEvent.setup()
    renderLogin(login)

    await fillAndSubmit(user)

    expect(await screen.findByText('Ошибка входа')).toBeInTheDocument()
  })

  it('блокирует кнопку на время запроса', async () => {
    let resolveLogin
    const login = vi.fn(
      () => new Promise((resolve) => { resolveLogin = resolve }),
    )
    const user = userEvent.setup()
    renderLogin(login)

    await user.type(screen.getByPlaceholderText('Email'), 'client@example.com')
    await user.type(screen.getByPlaceholderText('Пароль'), 'ClientPass123!')
    await user.click(screen.getByRole('button', { name: 'Войти' }))

    expect(screen.getByRole('button', { name: 'Войти' })).toBeDisabled()

    resolveLogin({})
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Войти' })).not.toBeInTheDocument(),
    )
  })
})
