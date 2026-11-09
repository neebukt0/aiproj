import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Reports() {
  const [resources, setResources] = useState([])
  const [start, setStart] = useState(new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10))
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10))
  const [resourceId, setResourceId] = useState('')
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/api/resources').then((res) => setResources(res.data)).catch(() => {})
  }, [])

  async function build(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/api/reports', {
        start_at: new Date(start + 'T00:00:00Z').toISOString(),
        end_at: new Date(end + 'T23:59:59Z').toISOString(),
        resource_id: resourceId || undefined,
      })
      setReport(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    } finally {
      setLoading(false)
    }
  }

  async function exportCsv() {
    try {
      const res = await api.post(
        '/api/reports/csv',
        {
          start_at: new Date(start + 'T00:00:00Z').toISOString(),
          end_at: new Date(end + 'T23:59:59Z').toISOString(),
          resource_id: resourceId || undefined,
        },
        { responseType: 'blob' },
      )
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'report.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка экспорта')
    }
  }

  return (
    <div>
      <h2>Отчёт</h2>
      <form onSubmit={build} className="filters">
        <label>
          С
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          По
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <select value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
          <option value="">Все объекты</option>
          {resources.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        <button disabled={loading} type="submit">
          Построить
        </button>
        <button disabled={loading} type="button" className="ghost" onClick={exportCsv}>
          CSV
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {loading && <div className="state">Загрузка...</div>}
      {report && (
        <table className="table">
          <thead>
            <tr>
              <th>Объект</th>
              <th>Всего</th>
              <th>Подтверждено</th>
              <th>Завершено</th>
              <th>Отменено</th>
              <th>Минут</th>
            </tr>
          </thead>
          <tbody>
            {report.rows.map((r) => (
              <tr key={r.resource_id}>
                <td>{r.resource_name}</td>
                <td>{r.total_bookings}</td>
                <td>{r.confirmed_bookings}</td>
                <td>{r.completed_bookings}</td>
                <td>{r.cancelled_bookings}</td>
                <td>{r.total_minutes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}