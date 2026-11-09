import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [bookings, setBookings] = useState([])
  const [bookingId, setBookingId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get('/api/bookings'),
      api.get('/api/logs'),
    ])
      .then(([b, l]) => {
        setBookings(b.data)
        setLogs(l.data)
      })
      .catch((err) => setError(err.response?.data?.detail || 'Ошибка'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="state">Загрузка...</div>
  if (error) return <div className="state error">{error}</div>

  const filtered = bookingId
    ? logs.filter((l) => l.booking_id === bookingId)
    : logs

  return (
    <div>
      <h2>Журнал действий</h2>
      <div className="filters">
        <select value={bookingId} onChange={(e) => setBookingId(e.target.value)}>
          <option value="">Все брони</option>
          {bookings.map((b) => (
            <option key={b.id} value={b.id}>
              #{b.id.slice(0, 8)} — {new Date(b.start_at).toLocaleString()}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="state">Записей нет</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Бронь</th>
              <th>От</th>
              <th>К</th>
              <th>Кем</th>
              <th>Когда</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((l) => (
              <tr key={l.id}>
                <td>#{l.booking_id.slice(0, 8)}</td>
                <td>{l.from_status || '—'}</td>
                <td>{l.to_status}</td>
                <td>{l.changed_by ? l.changed_by.slice(0, 8) : '—'}</td>
                <td>{new Date(l.changed_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}