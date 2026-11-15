import { useEffect, useState } from 'react'
import api from '../api/client'

const STATUS_LABEL = {
  created: 'Ожидает',
  confirmed: 'Подтверждено',
  completed: 'Завершено',
  cancelled: 'Отменено',
}

export default function Panel() {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [resourceId, setResourceId] = useState('')
  const [resources, setResources] = useState([])
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [acting, setActing] = useState(null)

  useEffect(() => {
    api.get('/api/resources').then((res) => setResources(res.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    setError('')
    api
      .get('/api/bookings', { params: { date, resource_id: resourceId || undefined } })
      .then((res) => setBookings(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Ошибка'))
      .finally(() => setLoading(false))
  }, [date, resourceId])

  async function changeStatus(id, status) {
    setActing(id)
    try {
      await api.post(`/api/bookings/${id}/status`, { status })
      setBookings((prev) =>
        prev.map((b) => (b.id === id ? { ...b, status } : b)),
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    } finally {
      setActing(null)
    }
  }

  const resourceName = (id) =>
    resources.find((r) => r.id === id)?.name || `Объект #${id.slice(0, 8)}`

  return (
    <div>
      <div className="page-head">
        <div>
          <span className="eyebrow">Панель сотрудника</span>
          <h1>Брони на день</h1>
          <p className="muted">
            Подтверждайте новые заявки и завершайте состоявшиеся мероприятия.
          </p>
        </div>
      </div>

      <div className="filters">
        <label>
          Дата
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <label>
          Объект
          <select value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
            <option value="">Все объекты</option>
            {resources.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <div className="state">Загрузка броней...</div>}
      {!loading && error && <div className="state error">{error}</div>}
      {!loading && !error && bookings.length === 0 && (
        <div className="state">
          <span className="empty-icon">📅</span>
          На {date} броней нет. Выберите другую дату.
        </div>
      )}

      {!loading && !error && bookings.length > 0 && (
        <div className="list">
          {bookings.map((b) => (
            <div className="booking" key={b.id}>
              <div>
                <strong>{resourceName(b.resource_id)}</strong>
                <p className="muted">
                  #{b.id.slice(0, 8)} ·{' '}
                  {new Date(b.start_at).toLocaleString()} —{' '}
                  {new Date(b.end_at).toLocaleString()}
                </p>
                <span className={`status ${b.status}`}>
                  {STATUS_LABEL[b.status] || b.status}
                </span>
              </div>
              <div className="actions">
                {b.status === 'created' && (
                  <button
                    disabled={acting === b.id}
                    onClick={() => changeStatus(b.id, 'confirmed')}
                  >
                    Подтвердить
                  </button>
                )}
                {b.status === 'confirmed' && (
                  <button
                    disabled={acting === b.id}
                    onClick={() => changeStatus(b.id, 'completed')}
                  >
                    Завершить
                  </button>
                )}
                {(b.status === 'created' || b.status === 'confirmed') && (
                  <button
                    disabled={acting === b.id}
                    className="ghost"
                    onClick={() => changeStatus(b.id, 'cancelled')}
                  >
                    Отменить
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
