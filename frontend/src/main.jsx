import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import Layout from './components/Layout.jsx'
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

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Catalog />} />
            <Route path="/book/:id" element={<Book />} />
            <Route path="/my" element={<MyBookings />} />
            <Route path="/panel" element={<Panel />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/logs" element={<Logs />} />
          </Route>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)