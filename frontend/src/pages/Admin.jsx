import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Admin() {
  const [users, setUsers] = useState([])
  const [resources, setResources] = useState([])
  const [error, setError] = useState('')

  async function load() {
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
  }

  useEffect(() => {
    load()
  }, [])

  async function toggleUser(u) {
    try {
      await api.patch(
        `/api/admin/users/${u.id}`,
        { is_active: !u.is_active },
        { headers: { Authorization: `Bearer ${localStorage.getItem('at')}` } },
      )
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    }
  }

  async function deleteUser(id) {
    if (!confirm('Удалить пользователя?')) return
    try {
      await api.delete(`/api/admin/users/${id}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('at')}` },
      })
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    }
  }

  async function deleteResource(id) {
    if (!confirm('Удалить объект?')) return
    try {
      await api.delete(`/api/resources/${id}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('at')}` } },
      )
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка')
    }
  }

  if (error) return <div className="state error">{error}</div>

  return (
    <div>
      <h2>Панель администратора</h2>

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