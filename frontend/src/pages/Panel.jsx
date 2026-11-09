import { useEffect, useState } from 'react'
import api from '../api/client'

const STATUS_LABEL = {
  created: 'Ожидает',
  confirmed: 'Подтверждено',
  completed: 'Завершено',
  cancelled: 'Отменено',
}

export default function Panel() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
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
      await api.post(
        `/api/bookings/${id}/status`,
        { status },
        { headers: { Authorization: `Bearer ${localStorage.getItem('at')}` } },
      )
      setBookings((prev) =>
        prev.map((b) => (b.id === id ? { ...b, status } : b)),
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    } finally {
      setActing(null)
    }
  }

  if (loading) return <div className="state">Загрузка...</div>
  if (error) return <div className="state error">{error}</div>
  if (bookings.length === 0)
    return <div className="state">На {date} броней нет</div>

  return (
    <div>
      <h2>Панель сотрудника</h2>
      <div className="filters">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <select value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
          <option value="">Все объекты</option>
          {resources.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>

      <div className="list">
        {bookings.map((b) => (
          <div className="booking" key={b.id}>
            <div>
              <strong>#{b.id.slice(0, 8)}</strong>
              <p className="muted">
                {new Date(b.start_at).toLocaleString()} —{' '}
                {new Date(b.end_at).toLocaleString()}
              </p>
              <span className={`status ${b.status}`}>
                {STATUS_LABEL[b.status] || b.status}
              </span>
            </div>
            <div className="actions">
              {b.status === 'created' && (
                <button disabled={acting === b.id} onClick={() => changeStatus(b.id, 'confirmed')}>
                  Подтвердить
                </button>
              )}
              {b.status === 'confirmed' && (
                <button disabled={acting === b.id} onClick={() => changeStatus(b.id, 'completed')}>
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
    </div>
  )
}