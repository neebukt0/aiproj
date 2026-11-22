import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import MyBookings from './MyBookings.jsx'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const RESOURCES = [
  { id: 'r1', name: 'Зал «Альфа»' },
  { id: 'r2', name: 'Переговорная «Инвестор»' },
]

const BOOKINGS = [
  {
    id: 'b1',
    resource_id: 'r1',
    status: 'created',
    start_at: '2030-01-15T10:00:00Z',
    end_at: '2030-01-15T12:00:00Z',
  },
  {
    id: 'b2',
    resource_id: 'r2',
    status: 'cancelled',
    start_at: '2030-01-16T10:00:00Z',
    end_at: '2030-01-16T12:00:00Z',
  },
]

function mockApi({ bookings = BOOKINGS, error } = {}) {
  api.get.mockImplementation((url) => {
    if (url === '/api/bookings/mine') {
      if (error) return Promise.reject(error)
      return Promise.resolve({ data: bookings })
    }
    if (url === '/api/resources') return Promise.resolve({ data: RESOURCES })
    return Promise.resolve({ data: [] })
  })
}

function renderPage(user = { role: 'client' }) {
  useAuth.mockReturnValue({ user })
  return render(<MyBookings />)
}

describe('MyBookings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('показывает актуальные брони и скрывает историю', async () => {
    mockApi()
    renderPage()

    expect(await screen.findByText('Зал «Альфа»')).toBeInTheDocument()
    expect(screen.getByText('Ожидает подтверждения')).toBeInTheDocument()
    expect(screen.queryByText('Переговорная «Инвестор»')).not.toBeInTheDocument()
  })

  it('переключается на историю', async () => {
    mockApi()
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Зал «Альфа»')

    await user.click(screen.getByRole('button', { name: 'История' }))

    expect(screen.getByText('Переговорная «Инвестор»')).toBeInTheDocument()
    expect(screen.getByText('Отменено')).toBeInTheDocument()
    expect(screen.queryByText('Зал «Альфа»')).not.toBeInTheDocument()
  })

  it('отменяет бронь и переносит её в историю', async () => {
    mockApi()
    api.post.mockResolvedValue({ data: { ok: true } })
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Зал «Альфа»')

    await user.click(screen.getByRole('button', { name: 'Отменить' }))

    expect(api.post).toHaveBeenCalledWith('/api/bookings/b1/status', {
      status: 'cancelled',
    })
    expect(await screen.findByText('Актуальных броней нет.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'История' }))
    expect(screen.getAllByText('Отменено')).toHaveLength(2)
  })

  it('показывает ошибку отмены и оставляет бронь актуальной', async () => {
    mockApi()
    api.post.mockRejectedValue({
      response: { data: { detail: 'Нельзя отменить бронь' } },
    })
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Зал «Альфа»')

    await user.click(screen.getByRole('button', { name: 'Отменить' }))

    expect(await screen.findByText('Нельзя отменить бронь')).toBeInTheDocument()
    expect(screen.getByText('Зал «Альфа»')).toBeInTheDocument()
  })

  it('показывает пустое состояние без броней', async () => {
    mockApi({ bookings: [] })
    renderPage()

    expect(
      await screen.findByText(/У вас пока нет броней/),
    ).toBeInTheDocument()
  })

  it('показывает ошибку загрузки', async () => {
    mockApi({ error: { response: { data: { detail: 'Нет доступа' } } } })
    renderPage()

    expect(await screen.findByText('Нет доступа')).toBeInTheDocument()
  })

  it('подставляет объект по id, если название не найдено', async () => {
    mockApi({
      bookings: [
        {
          id: 'b3',
          resource_id: 'unknown-1234567890',
          status: 'confirmed',
          start_at: '2030-01-17T10:00:00Z',
          end_at: '2030-01-17T12:00:00Z',
        },
      ],
    })
    renderPage()

    expect(await screen.findByText('Объект #unknown-')).toBeInTheDocument()
    expect(screen.getByText('Подтверждено')).toBeInTheDocument()
  })
})
