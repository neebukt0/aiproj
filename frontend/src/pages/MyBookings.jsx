import { useEffect, useState } from 'react'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export default function MyBookings() {
  const { user } = useAuth()
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [acting, setActing] = useState(null)

  useEffect(() => {
    if (!user) return
    setLoading(true)
    api
      .get('/api/bookings/mine')
      .then((res) => setBookings(res.data))
      .catch((err) => setError(err.response?.data?.detail || 'Ошибка'))
      .finally(() => setLoading(false))
  }, [user])

  async function cancel(id) {
    setActing(id)
    try {
      await api.post(
        `/api/bookings/${id}/status`,
        { status: 'cancelled' },
        { headers: { Authorization: `Bearer ${localStorage.getItem('at')}` } },
      )
      setBookings((prev) =>
        prev.map((b) => (b.id === id ? { ...b, status: 'cancelled' } : b)),
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка отмены')
    } finally {
      setActing(null)
    }
  }

  if (loading) return <div className="state">Загрузка...</div>
  if (error) return <div className="state error">{error}</div>
  if (bookings.length === 0)
    return <div className="state">У вас пока нет броней</div>

  const statusLabel = {
    created: 'Ожидает подтверждения',
    confirmed: 'Подтверждено',
    completed: 'Завершено',
    cancelled: 'Отменено',
  }

  return (
    <div>
      <h2>Мои брони</h2>
      <div className="list">
        {bookings.map((b) => (
          <div className="booking" key={b.id}>
            <div>
              <strong>Бронь #{b.id.slice(0, 8)}</strong>
              <p className="muted">
                {new Date(b.start_at).toLocaleString()} —{' '}
                {new Date(b.end_at).toLocaleString()}
              </p>
              <span className={`status ${b.status}`}>
                {statusLabel[b.status] || b.status}
              </span>
            </div>
            {b.status === 'created' && (
              <button disabled={acting === b.id} onClick={() => cancel(b.id)}>
                Отменить
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}