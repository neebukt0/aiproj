import { useEffect, useState } from 'react'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const STATUS_LABEL = {
  created: 'Ожидает подтверждения',
  confirmed: 'Подтверждено',
  completed: 'Завершено',
  cancelled: 'Отменено',
}

export default function MyBookings() {
  const { user } = useAuth()
  const [bookings, setBookings] = useState([])
  const [resources, setResources] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [acting, setActing] = useState(null)

  useEffect(() => {
    if (!user) return
    setLoading(true)
    Promise.all([api.get('/api/bookings/mine'), api.get('/api/resources')])
      .then(([b, r]) => {
        setBookings(b.data)
        setResources(r.data)
      })
      .catch((err) => setError(err.response?.data?.detail || 'Ошибка'))
      .finally(() => setLoading(false))
  }, [user])

  async function cancel(id) {
    setActing(id)
    setActionError('')
    try {
      await api.post(`/api/bookings/${id}/status`, { status: 'cancelled' })
      setBookings((prev) =>
        prev.map((b) => (b.id === id ? { ...b, status: 'cancelled' } : b)),
      )
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Ошибка отмены')
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
          <span className="eyebrow">Личный кабинет</span>
          <h1>Мои брони</h1>
          <p className="muted">
            Здесь собраны ваши заявки. Неподтверждённая бронь освобождает место
            через 10 минут.
          </p>
        </div>
      </div>

      {loading && <div className="state">Загрузка броней...</div>}
      {!loading && error && <div className="state error">{error}</div>}
      {!loading && !error && actionError && <p className="error">{actionError}</p>}
      {!loading && !error && bookings.length === 0 && (
        <div className="state">
          <span className="empty-icon">🎟️</span>
          У вас пока нет броней. Выберите площадку в каталоге.
        </div>
      )}

      {!loading && !error && bookings.length > 0 && (
        <div className="list">
          {bookings.map((b) => (
            <div className="booking" key={b.id}>
              <div>
                <strong>{resourceName(b.resource_id)}</strong>
                <p className="muted">
                  {new Date(b.start_at).toLocaleString()} —{' '}
                  {new Date(b.end_at).toLocaleString()}
                </p>
                <span className={`status ${b.status}`}>
                  {STATUS_LABEL[b.status] || b.status}
                </span>
              </div>
              {(b.status === 'created' || b.status === 'confirmed') && (
                <button
                  className="ghost danger"
                  disabled={acting === b.id}
                  onClick={() => cancel(b.id)}
                >
                  Отменить
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
