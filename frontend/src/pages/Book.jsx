import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export default function Book() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [resource, setResource] = useState(null)
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setLoading(true)
    api
      .get(`/api/resources/${id}`)
      .then((res) => setResource(res.data))
      .catch(() => setError('Объект не найден'))
      .finally(() => setLoading(false))
  }, [id])

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!user) {
      navigate('/login')
      return
    }
    setSubmitting(true)
    try {
      const res = await api.post(
        '/api/bookings',
        {
          resource_id: id,
          start_at: new Date(start).toISOString(),
          end_at: new Date(end).toISOString(),
        },
        { headers: { Authorization: `Bearer ${localStorage.getItem('at')}` } },
      )
      navigate('/my')
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка бронирования')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="state">Загрузка...</div>
  if (error && !resource) return <div className="state error">{error}</div>

  return (
    <div className="book">
      <h2>Бронирование: {resource?.name}</h2>
      <p className="muted">
        {resource?.resource_type} · вмещает {resource?.capacity}
      </p>
      <form onSubmit={submit} className="booking-form">
        <label>
          Начало
          <input
            type="datetime-local"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            required
          />
        </label>
        <label>
          Окончание
          <input
            type="datetime-local"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button disabled={submitting} type="submit">
          Забронировать
        </button>
      </form>
      <p className="muted hint">
        Место удерживается 10 минут. Если не подтвердить — освобождается.
      </p>
      <Link to="/" className="back">
        ← Назад
      </Link>
    </div>
  )
}