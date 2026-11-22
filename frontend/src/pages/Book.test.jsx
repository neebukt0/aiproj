import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import Book from './Book.jsx'

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

const RESOURCE = {
  id: 'r1',
  name: 'Зал «Альфа»',
  resource_type: 'hall',
  capacity: 80,
}

function mockApi({ busy = [], resource = RESOURCE, availabilityError } = {}) {
  api.get.mockImplementation((url) => {
    if (url === '/api/resources/r1') {
      return resource
        ? Promise.resolve({ data: resource })
        : Promise.reject(new Error('404'))
    }
    if (url === '/api/resources/r1/availability') {
      if (availabilityError) return Promise.reject(availabilityError)
      return Promise.resolve({ data: { busy } })
    }
    return Promise.resolve({ data: {} })
  })
}

function renderBook(user = { role: 'client' }) {
  useAuth.mockReturnValue({ user })

  return render(
    <MemoryRouter initialEntries={['/book/r1']}>
      <Routes>
        <Route path="/book/:id" element={<Book />} />
        <Route path="/my" element={<div>мои брони открыты</div>} />
        <Route path="/login" element={<div>форма входа</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

async function fillTimes(start = '2030-01-15T10:00', end = '2030-01-15T12:00') {
  fireEvent.change(screen.getByLabelText(/Начало/), {
    target: { value: start },
  })
  fireEvent.change(screen.getByLabelText(/Окончание/), {
    target: { value: end },
  })
}

describe('Book', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('показывает объект и занятость на день', async () => {
    mockApi({
      busy: [
        {
          start_at: '2030-01-15T10:00:00Z',
          end_at: '2030-01-15T12:00:00Z',
          status: 'confirmed',
        },
      ],
    })
    renderBook()

    expect(await screen.findByText('Зал «Альфа»')).toBeInTheDocument()
    expect(screen.getByText(/Зал · вмещает 80/)).toBeInTheDocument()
    expect(await screen.findByText('подтверждено')).toBeInTheDocument()
  })

  it('сообщает, что день свободен', async () => {
    mockApi({ busy: [] })
    renderBook()

    expect(
      await screen.findByText('На этот день всё свободно — можно бронировать.'),
    ).toBeInTheDocument()
  })

  it('показывает ошибку проверки занятости', async () => {
    mockApi({
      availabilityError: {
        response: { data: { detail: 'Не удалось проверить занятость' } },
      },
    })
    renderBook()

    expect(
      await screen.findByText('Не удалось проверить занятость'),
    ).toBeInTheDocument()
  })

  it('показывает ошибку, если объект не найден', async () => {
    mockApi({ resource: null })
    renderBook()

    expect(await screen.findByText('Объект не найден')).toBeInTheDocument()
  })

  it('валидирует порядок времени', async () => {
    mockApi()
    const user = userEvent.setup()
    renderBook()
    await screen.findByText('Зал «Альфа»')

    await fillTimes('2030-01-15T12:00', '2030-01-15T10:00')
    await user.click(screen.getByRole('button', { name: 'Забронировать' }))

    expect(
      await screen.findByText('Окончание должно быть позже начала'),
    ).toBeInTheDocument()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('создаёт бронь и переходит в «Мои брони»', async () => {
    mockApi()
    api.post.mockResolvedValue({ data: { id: 'b1' } })
    const user = userEvent.setup()
    renderBook()
    await screen.findByText('Зал «Альфа»')

    await fillTimes()
    await user.click(screen.getByRole('button', { name: 'Забронировать' }))

    expect(await screen.findByText('мои брони открыты')).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('/api/bookings', {
      resource_id: 'r1',
      start_at: new Date('2030-01-15T10:00').toISOString(),
      end_at: new Date('2030-01-15T12:00').toISOString(),
    })
  })

  it('показывает ошибку сервера при бронировании', async () => {
    mockApi()
    api.post.mockRejectedValue({
      response: { data: { detail: 'Resource already booked' } },
    })
    const user = userEvent.setup()
    renderBook()
    await screen.findByText('Зал «Альфа»')

    await fillTimes()
    await user.click(screen.getByRole('button', { name: 'Забронировать' }))

    expect(
      await screen.findByText('Resource already booked'),
    ).toBeInTheDocument()
    expect(screen.queryByText('мои брони открыты')).not.toBeInTheDocument()
  })

  it('отправляет неавторизованного пользователя на вход', async () => {
    mockApi()
    const user = userEvent.setup()
    renderBook(null)
    await screen.findByText('Зал «Альфа»')

    await fillTimes()
    await user.click(screen.getByRole('button', { name: 'Забронировать' }))

    expect(await screen.findByText('форма входа')).toBeInTheDocument()
    expect(api.post).not.toHaveBeenCalled()
  })

  it('перезапрашивает занятость после ошибки бронирования', async () => {
    mockApi()
    api.post.mockRejectedValue(new Error('network'))
    const user = userEvent.setup()
    renderBook()
    await screen.findByText('Зал «Альфа»')
    const callsBefore = api.get.mock.calls.filter(([url]) =>
      url.endsWith('/availability'),
    ).length

    await fillTimes()
    await user.click(screen.getByRole('button', { name: 'Забронировать' }))

    await waitFor(() => {
      const callsAfter = api.get.mock.calls.filter(([url]) =>
        url.endsWith('/availability'),
      ).length
      expect(callsAfter).toBeGreaterThan(callsBefore)
    })
  })
})
