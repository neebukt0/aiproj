import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../api/client'
import Admin from './Admin.jsx'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const USERS = [
  {
    id: 'u1',
    email: 'client@example.com',
    role: 'client',
    is_active: true,
  },
  {
    id: 'u2',
    email: 'employee@example.com',
    role: 'employee',
    is_active: false,
  },
]

const RESOURCES = [
  {
    id: 'r1',
    name: 'Зал «Альфа»',
    resource_type: 'hall',
    capacity: 80,
  },
]

function mockApi({ users = USERS, resources = RESOURCES, loadError } = {}) {
  api.get.mockImplementation((url) => {
    if (loadError) return Promise.reject(loadError)
    if (url === '/api/admin/users') return Promise.resolve({ data: users })
    if (url === '/api/resources') return Promise.resolve({ data: resources })
    return Promise.resolve({ data: [] })
  })
}

describe('Admin', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.confirm = vi.fn(() => true)
  })

  it('показывает пользователей и объекты', async () => {
    mockApi()
    render(<Admin />)

    expect(await screen.findByText('client@example.com')).toBeInTheDocument()
    expect(screen.getByText('employee@example.com')).toBeInTheDocument()
    expect(screen.getByText('Зал «Альфа»')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Заблокировать' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Активировать' })).toBeInTheDocument()
  })

  it('создаёт пользователя и показывает уведомление', async () => {
    mockApi()
    api.post.mockResolvedValue({ data: { id: 'u3' } })
    const user = userEvent.setup()
    render(<Admin />)
    await screen.findByText('client@example.com')

    await user.type(screen.getByPlaceholderText('Email'), 'new@example.com')
    await user.type(
      screen.getByPlaceholderText('Пароль (минимум 8 символов)'),
      'NewPass123!',
    )
    await user.selectOptions(screen.getAllByRole('combobox').at(-1), 'employee')
    await user.click(screen.getByRole('button', { name: 'Создать' }))

    expect(api.post).toHaveBeenCalledWith('/api/admin/users', {
      email: 'new@example.com',
      password: 'NewPass123!',
      role: 'employee',
    })
    expect(
      await screen.findByText('Пользователь new@example.com создан'),
    ).toBeInTheDocument()
  })

  it('показывает ошибку создания пользователя', async () => {
    mockApi()
    api.post.mockRejectedValue({
      response: { data: { detail: 'Email уже занят' } },
    })
    const user = userEvent.setup()
    render(<Admin />)
    await screen.findByText('client@example.com')

    await user.type(screen.getByPlaceholderText('Email'), 'client@example.com')
    await user.type(
      screen.getByPlaceholderText('Пароль (минимум 8 символов)'),
      'NewPass123!',
    )
    await user.click(screen.getByRole('button', { name: 'Создать' }))

    expect(await screen.findByText('Email уже занят')).toBeInTheDocument()
  })

  it('блокирует и удаляет пользователя', async () => {
    mockApi()
    api.patch.mockResolvedValue({ data: { ok: true } })
    api.delete.mockResolvedValue({ data: { ok: true } })
    const user = userEvent.setup()
    render(<Admin />)
    await screen.findByText('client@example.com')

    await user.click(screen.getByRole('button', { name: 'Заблокировать' }))
    expect(api.patch).toHaveBeenCalledWith('/api/admin/users/u1', {
      is_active: false,
    })

    const row = screen.getByText('client@example.com').closest('tr')
    await user.click(within(row).getByRole('button', { name: 'Удалить' }))

    expect(window.confirm).toHaveBeenCalledWith('Удалить пользователя?')
    expect(api.delete).toHaveBeenCalledWith('/api/admin/users/u1')
  })

  it('удаляет объект после подтверждения', async () => {
    mockApi()
    api.delete.mockResolvedValue({ data: { ok: true } })
    const user = userEvent.setup()
    render(<Admin />)
    await screen.findByText('Зал «Альфа»')

    const row = screen.getByText('Зал «Альфа»').closest('tr')
    await user.click(within(row).getByRole('button', { name: 'Удалить' }))

    expect(api.delete).toHaveBeenCalledWith('/api/resources/r1')
  })

  it('не удаляет пользователя без подтверждения', async () => {
    mockApi()
    window.confirm = vi.fn(() => false)
    const user = userEvent.setup()
    render(<Admin />)
    await screen.findByText('client@example.com')

    const row = screen.getByText('client@example.com').closest('tr')
    await user.click(within(row).getByRole('button', { name: 'Удалить' }))

    expect(api.delete).not.toHaveBeenCalled()
  })

  it('показывает пустые состояния', async () => {
    mockApi({ users: [], resources: [] })
    render(<Admin />)

    expect(await screen.findByText('Пользователей нет')).toBeInTheDocument()
    expect(screen.getByText('Объектов нет')).toBeInTheDocument()
  })

  it('показывает ошибку загрузки', async () => {
    mockApi({ loadError: { response: { data: { detail: 'Нет доступа' } } } })
    render(<Admin />)

    expect(await screen.findByText('Нет доступа')).toBeInTheDocument()
  })

  it('перезагружает списки после изменения', async () => {
    mockApi()
    api.patch.mockResolvedValue({ data: { ok: true } })
    const user = userEvent.setup()
    render(<Admin />)
    await screen.findByText('client@example.com')
    const callsBefore = api.get.mock.calls.length

    await user.click(screen.getByRole('button', { name: 'Заблокировать' }))

    await waitFor(() =>
      expect(api.get.mock.calls.length).toBeGreaterThan(callsBefore),
    )
  })
})
