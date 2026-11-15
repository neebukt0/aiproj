import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const TYPE_LABEL = {
  hall: 'Зал',
  private_room: 'Переговорная',
}

const STATUS_LABEL = {
  created: 'удерживается',
  confirmed: 'подтверждено',
}

function localToday() {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10)
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

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

  const [busy, setBusy] = useState([])
  const [busyLoading, setBusyLoading] = useState(true)
  const [busyError, setBusyError] = useState('')
  const [reload, setReload] = useState(0)

  const date = start ? start.slice(0, 10) : localToday()

  useEffect(() => {
    setLoading(true)
    api
      .get(`/api/resources/${id}`)
      .then((res) => setResource(res.data))
      .catch(() => setError('Объект не найден'))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    setBusyLoading(true)
    setBusyError('')
    api
      .get(`/api/resources/${id}/availability`, { params: { date } })
      .then((res) => setBusy(res.data.busy || []))
      .catch((err) => setBusyError(err.response?.data?.detail || 'Не удалось проверить занятость'))
      .finally(() => setBusyLoading(false))
  }, [id, date, reload])

  async function submit(e) {
    e.preventDefault()
    setError('')

    if (!user) {
      navigate('/login')
      return
    }
    if (!start || !end || new Date(end) <= new Date(start)) {
      setError('Окончание должно быть позже начала')
      return
    }

    setSubmitting(true)
    try {
      await api.post('/api/bookings', {
        resource_id: id,
        start_at: new Date(start).toISOString(),
        end_at: new Date(end).toISOString(),
      })
      navigate('/my')
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка бронирования')
      setReload((value) => value + 1)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="state">Загрузка...</div>
  if (error && !resource) return <div className="state error">{error}</div>

  const dateLabel = new Date(`${date}T00:00:00`).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <div className="book">
      <Link to="/" className="back">
        ← Назад в каталог
      </Link>
      <div className="page-head">
        <div>
          <span className="eyebrow">Бронирование</span>
          <h1>{resource?.name}</h1>
          <p className="muted">
            {TYPE_LABEL[resource?.resource_type] || resource?.resource_type} · вмещает{' '}
            {resource?.capacity}
          </p>
        </div>
      </div>

      <div className="book-grid">
        <form onSubmit={submit} className="booking-form card-form">
          <h3>Выберите время</h3>
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
            {submitting ? 'Бронируем...' : 'Забронировать'}
          </button>
          <p className="muted hint">
            Место удерживается 10 минут. Если не подтвердить — освобождается.
          </p>
        </form>

        <aside className="availability">
          <div className="availability-head">
            <h3>Занятость</h3>
            <span className="muted">{dateLabel}</span>
          </div>
          {busyLoading && <p className="muted">Проверяем занятость...</p>}
          {!busyLoading && busyError && <p className="error">{busyError}</p>}
          {!busyLoading && !busyError && busy.length === 0 && (
            <p className="muted">На этот день всё свободно — можно бронировать.</p>
          )}
          {!busyLoading && !busyError && busy.length > 0 && (
            <ul className="busy-list">
              {busy.map((item) => (
                <li key={`${item.start_at}-${item.end_at}`}>
                  <span>
                    {formatTime(item.start_at)} — {formatTime(item.end_at)}
                  </span>
                  <span className={`status ${item.status}`}>
                    {STATUS_LABEL[item.status] || item.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  )
}
