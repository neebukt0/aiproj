import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import api from '../api/client'
import Catalog from './Catalog.jsx'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

const RESOURCES = [
  {
    id: 'r1',
    name: 'Зал «Альфа»',
    resource_type: 'hall',
    capacity: 80,
    description: 'Большой зал',
  },
  {
    id: 'r2',
    name: 'Переговорная «Инвестор»',
    resource_type: 'private_room',
    capacity: 8,
    description: '',
  },
]

function renderCatalog() {
  return render(
    <MemoryRouter>
      <Catalog />
    </MemoryRouter>,
  )
}

describe('Catalog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('загружает и показывает площадки', async () => {
    api.get.mockResolvedValue({ data: RESOURCES })
    renderCatalog()

    expect(await screen.findByText('Зал «Альфа»')).toBeInTheDocument()
    expect(screen.getByText('Переговорная «Инвестор»')).toBeInTheDocument()
    expect(screen.getByText(/Зал · вмещает 80/)).toBeInTheDocument()
    expect(screen.getByText(/Переговорная · вмещает 8/)).toBeInTheDocument()
    expect(screen.getByText('Большой зал')).toBeInTheDocument()

    expect(api.get).toHaveBeenCalledWith('/api/resources', {
      params: {
        skip: 0,
        limit: 13,
        search: undefined,
        resource_type: undefined,
      },
    })
  })

  it('ищет по названию и сбрасывает страницу', async () => {
    api.get.mockResolvedValue({ data: RESOURCES })
    const user = userEvent.setup()
    renderCatalog()
    await screen.findByText('Зал «Альфа»')

    await user.type(screen.getByPlaceholderText('Поиск по названию'), 'Альфа')

    await waitFor(() => {
      const lastCall = api.get.mock.calls.at(-1)
      expect(lastCall[1].params.search).toBe('Альфа')
      expect(lastCall[1].params.skip).toBe(0)
    })
  })

  it('фильтрует по типу площадки', async () => {
    api.get.mockResolvedValue({ data: RESOURCES })
    const user = userEvent.setup()
    renderCatalog()
    await screen.findByText('Зал «Альфа»')

    await user.selectOptions(screen.getByRole('combobox'), 'private_room')

    await waitFor(() => {
      const lastCall = api.get.mock.calls.at(-1)
      expect(lastCall[1].params.resource_type).toBe('private_room')
    })
  })

  it('показывает пустое состояние', async () => {
    api.get.mockResolvedValue({ data: [] })
    renderCatalog()

    expect(
      await screen.findByText(/По вашему запросу ничего не найдено/),
    ).toBeInTheDocument()
  })

  it('показывает ошибку загрузки', async () => {
    api.get.mockRejectedValue({
      response: { data: { detail: 'Сервер недоступен' } },
    })
    renderCatalog()

    expect(await screen.findByText('Сервер недоступен')).toBeInTheDocument()
  })

  it('переключает страницы и запрашивает следующий блок', async () => {
    const firstPage = Array.from({ length: 13 }, (_, i) => ({
      id: `r${i}`,
      name: `Площадка ${i + 1}`,
      resource_type: 'hall',
      capacity: 10 + i,
    }))
    api.get
      .mockResolvedValueOnce({ data: firstPage })
      .mockResolvedValueOnce({
        data: [{ id: 'r13', name: 'Площадка 13', resource_type: 'hall', capacity: 22 }],
      })
    const user = userEvent.setup()
    renderCatalog()

    await screen.findByText('Площадка 1')
    expect(screen.getByText('Страница 1')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Вперёд' }))

    await waitFor(() => {
      const lastCall = api.get.mock.calls.at(-1)
      expect(lastCall[1].params.skip).toBe(12)
    })
    expect(await screen.findByText('Страница 2')).toBeInTheDocument()
  })
})
