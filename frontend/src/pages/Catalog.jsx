import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

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

  if (loading) return <div className="state">Загрузка...</div>
  if (error) return <div className="state error">{error}</div>
  if (resources.length === 0)
    return <div className="state">Объектов не найдено</div>

  return (
    <div>
      <div className="filters">
        <input
          type="text"
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

      <div className="grid">
        {resources.map((r) => (
          <Link to={`/book/${r.id}`} key={r.id} className="card">
            {r.image && <img src={r.image} alt={r.name} />}
            <div className="card-body">
              <h3>{r.name}</h3>
              <p className="muted">
                {r.resource_type} · вмещает {r.capacity}
              </p>
              {r.description && <p className="desc">{r.description}</p>}
              <span className="cta">Забронировать</span>
            </div>
          </Link>
        ))}
      </div>

      <div className="pagination">
        <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
          Назад
        </button>
        <span>Страница {page + 1}</span>
        <button onClick={() => setPage((p) => p + 1)}>Вперёд</button>
      </div>
    </div>
  )
}