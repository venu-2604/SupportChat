import { Routes, Route, Link, useNavigate, Navigate } from 'react-router-dom'
import FAQs from './admin/FAQs'
import Tickets from './admin/Tickets'
import Analytics from './admin/Analytics'
import Users from './admin/Users'
import { useEffect } from 'react'
import { api } from '../lib/api'

export default function Admin() {
  const navigate = useNavigate()
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { navigate('/login'); return }
    api.get('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } }).catch(() => navigate('/login'))
  }, [navigate])
  return (
    <div className="grid grid-cols-[200px_1fr] gap-4">
      <aside className="bg-white border rounded p-3 space-y-2">
        <div className="font-semibold">Admin</div>
        <nav className="flex flex-col gap-2">
          <Link to="faqs">FAQs</Link>
          <Link to="tickets">Tickets</Link>
          <Link to="analytics">Analytics</Link>
          <Link to="users">Users</Link>
        </nav>
      </aside>
      <section>
        <Routes>
          <Route index element={<Navigate to="tickets" replace />} />
          <Route path="faqs" element={<FAQs />} />
          <Route path="tickets" element={<Tickets />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="users" element={<Users />} />
        </Routes>
      </section>
    </div>
  )
}


