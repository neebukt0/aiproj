import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

const TYPE_LABEL = {
  hall: 'Зал',
  private_room: 'Переговорная',
}

const TYPE_ICON = {
  hall: '🏛️',
  private_room: '🚪',
}

export default function Catalog() {
  const [resources, setResources] = useState([])
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)
  const limit = 12

  useEffect(() => {
    setLoading(true)
    setError('')
    api
      .get('/api/resources', {
        params: {
          skip: page * limit,
          limit,
          search: search || undefined,
          resource_type: type || undefined,
        },
      })
      .then((res) => setResources(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [page, search, type])

  const hasMore = resources.length === limit

  return (
    <div>
      <div className="page-head">
        <div>
          <span className="eyebrow">Каталог площадок</span>
          <h1>Найдите место для мероприятия</h1>
          <p className="muted">
            Залы и переговорные с онлайн-бронированием. Выберите площадку, укажите
            время — место закрепится за вами на 10 минут.
          </p>
        </div>
        <div className="hero-chips">
          <span className="chip">🏛️ Залы</span>
          <span className="chip">🚪 Переговорные</span>
          <span className="chip">⚡ Онлайн-бронирование</span>
        </div>
      </div>

      <div className="filters">
        <input
          type="text"
          className="grow"
          placeholder="Поиск по названию"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(0)
          }}
        />
        <select
          value={type}
          onChange={(e) => {
            setType(e.target.value)
            setPage(0)
          }}
        >
          <option value="">Все типы</option>
          <option value="hall">Зал</option>
          <option value="private_room">Переговорная</option>
        </select>
      </div>

      {loading && <div className="state">Загрузка площадок...</div>}
      {!loading && error && <div className="state error">{error}</div>}
      {!loading && !error && resources.length === 0 && (
        <div className="state">
          <span className="empty-icon">🔍</span>
          По вашему запросу ничего не найдено. Попробуйте изменить фильтры.
        </div>
      )}

      {!loading && !error && resources.length > 0 && (
        <>
          <div className="grid">
            {resources.map((r) => (
              <Link to={`/book/${r.id}`} key={r.id} className="card">
                <div className="card-media">
                  {r.image ? (
                    <img src={r.image} alt={r.name} />
                  ) : (
                    <span>{TYPE_ICON[r.resource_type] || '🎫'}</span>
                  )}
                </div>
                <div className="card-body">
                  <h3>{r.name}</h3>
                  <p className="muted">
                    {TYPE_LABEL[r.resource_type] || r.resource_type} · вмещает{' '}
                    {r.capacity}
                  </p>
                  {r.description && <p className="desc">{r.description}</p>}
                  <span className="cta">Забронировать</span>
                </div>
              </Link>
            ))}
          </div>

          <div className="pagination">
            <button
              className="ghost"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Назад
            </button>
            <span>Страница {page + 1}</span>
            <button
              className="ghost"
              disabled={!hasMore}
              onClick={() => setPage((p) => p + 1)}
            >
              Вперёд
            </button>
          </div>
        </>
      )}
    </div>
  )
}
