import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ThemeToggle from './ThemeToggle.jsx'

export default function Layout() {
  const { user, logout } = useAuth()
  const loc = useLocation()
  const isAuth = loc.pathname === '/login' || loc.pathname === '/register'

  if (isAuth) {
    return (
      <>
        <ThemeToggle floating />
        <Outlet />
      </>
    )
  }

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          🎫 Мероприятия
        </Link>
        <nav className="nav">
          <Link to="/">Каталог</Link>
          {user && user.role === 'client' && <Link to="/my">Мои брони</Link>}
          {user && (user.role === 'employee' || user.role === 'admin') && (
            <>
              <Link to="/panel">Панель</Link>
              <Link to="/reports">Отчёт</Link>
              <Link to="/logs">Журнал</Link>
            </>
          )}
          {user && user.role === 'admin' && <Link to="/admin">Админ</Link>}
        </nav>
        <div className="user">
          <ThemeToggle />
          {user ? (
            <>
              <span className="role">{user.role}</span>
              <button onClick={logout}>Выйти</button>
            </>
          ) : (
            <Link to="/login">Вход</Link>
          )}
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}