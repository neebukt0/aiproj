import { useCallback, useEffect, useState } from 'react'
import api from '../api/client'

const EMPTY_FORM = { email: '', password: '', role: 'client' }

export default function Admin() {
  const [users, setUsers] = useState([])
  const [resources, setResources] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    try {
      const [u, r] = await Promise.all([
        api.get('/api/admin/users'),
        api.get('/api/resources'),
      ])
      setUsers(u.data)
      setResources(r.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function createUser(e) {
    e.preventDefault()
    setError('')
    setNotice('')
    setCreating(true)
    try {
      await api.post('/api/admin/users', form)
      setNotice(`Пользователь ${form.email} создан`)
      setForm(EMPTY_FORM)
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка создания пользователя')
    } finally {
      setCreating(false)
    }
  }

  async function toggleUser(u) {
    setError('')
    try {
      await api.patch(`/api/admin/users/${u.id}`, { is_active: !u.is_active })
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    }
  }

  async function deleteUser(id) {
    if (!confirm('Удалить пользователя?')) return
    setError('')
    try {
      await api.delete(`/api/admin/users/${id}`)
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    }
  }

  async function deleteResource(id) {
    if (!confirm('Удалить объект?')) return
    setError('')
    try {
      await api.delete(`/api/resources/${id}`)
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    }
  }

  return (
    <div>
      <h2>Панель администратора</h2>

      {error && <p className="error">{error}</p>}
      {notice && <p className="muted">{notice}</p>}

      <h3>Новый пользователь</h3>
      <form onSubmit={createUser} className="filters">
        <input
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          required
        />
        <input
          type="password"
          placeholder="Пароль (минимум 8 символов)"
          minLength={8}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
        <select
          value={form.role}
          onChange={(e) => setForm({ ...form, role: e.target.value })}
        >
          <option value="client">Клиент</option>
          <option value="employee">Сотрудник</option>
          <option value="admin">Администратор</option>
        </select>
        <button disabled={creating} type="submit">
          Создать
        </button>
      </form>

      <h3>Пользователи</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Роль</th>
            <th>Активен</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.role}</td>
              <td>{u.is_active ? 'да' : 'нет'}</td>
              <td>
                <button className="ghost" onClick={() => toggleUser(u)}>
                  {u.is_active ? 'Заблокировать' : 'Активировать'}
                </button>{' '}
                <button className="ghost danger" onClick={() => deleteUser(u.id)}>
                  Удалить
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Объекты</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Название</th>
            <th>Тип</th>
            <th>Вместимость</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {resources.map((r) => (
            <tr key={r.id}>
              <td>{r.name}</td>
              <td>{r.resource_type}</td>
              <td>{r.capacity}</td>
              <td>
                <button className="ghost danger" onClick={() => deleteResource(r.id)}>
                  Удалить
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
