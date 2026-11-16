import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Catalog from './pages/Catalog.jsx'
import Book from './pages/Book.jsx'
import MyBookings from './pages/MyBookings.jsx'
import Panel from './pages/Panel.jsx'
import Admin from './pages/Admin.jsx'
import Reports from './pages/Reports.jsx'
import Logs from './pages/Logs.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx'

const STAFF = ['employee', 'admin']

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Catalog />} />
            <Route path="/book/:id" element={<Book />} />
            <Route
              path="/my"
              element={
                <ProtectedRoute>
                  <MyBookings />
                </ProtectedRoute>
              }
            />
            <Route
              path="/panel"
              element={
                <ProtectedRoute roles={STAFF}>
                  <Panel />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute roles={['admin']}>
                  <Admin />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute roles={STAFF}>
                  <Reports />
                </ProtectedRoute>
              }
            />
            <Route
              path="/logs"
              element={
                <ProtectedRoute roles={STAFF}>
                  <Logs />
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
