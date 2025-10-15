import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

function authHeader() {
  const t = localStorage.getItem('token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}

type Session = {
  session_id?: string
  user_email?: string
  customer_name?: string
  subject?: string
  category?: string
  last_message_role?: string
  last_message?: string
  last_at?: string
  started_at?: string
  status?: string
  priority?: string
  has_prefill?: boolean
}

type RegisteredUser = {
  id: number
  email: string
  is_admin: boolean
  created_at: string
}

export default function Users() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [registeredUsers, setRegisteredUsers] = useState<RegisteredUser[]>([])
  const [cases, setCases] = useState<any[]>([])
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [prefill, setPrefill] = useState('all')
  const [activeTab, setActiveTab] = useState<'users' | 'sessions'>('users')

  const load = async () => {
    try {
      // Load registered users
      const usersRes = await api.get('/api/admin/users', { headers: authHeader() })
      setRegisteredUsers(usersRes.data.users || [])
    } catch (error) {
      console.error('Failed to load registered users:', error)
    }

    try {
      // Load chat sessions
      const { data } = await api.get('/api/admin/users-live', { headers: authHeader() })
      setSessions(data.sessions || [])
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
    }

    try {
      const table = await api.get('/api/admin/cases-table', { headers: authHeader() })
      setCases(table.data.items || [])
    } catch {}
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])

  const filteredUsers = registeredUsers.filter(user => {
    const hay = `${user.email}`.toLowerCase()
    return !q || hay.includes(q.toLowerCase())
  })

  const filteredSessions = sessions.filter(s => {
    const hay = `${s.user_email||''} ${s.customer_name||''} ${s.subject||''}`.toLowerCase()
    const okQ = !q || hay.includes(q.toLowerCase())
    const okS = !status || (s.status||'').toLowerCase() === status
    const okP = prefill === 'all' || (prefill === 'with' ? !!s.has_prefill : !s.has_prefill)
    return okQ && okS && okP
  })

  return (
    <div className="space-y-4">
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b">
        <button 
          className={`px-4 py-2 ${activeTab === 'users' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-600'}`}
          onClick={() => setActiveTab('users')}
        >
          Registered Users ({registeredUsers.length})
        </button>
        <button 
          className={`px-4 py-2 ${activeTab === 'sessions' ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-600'}`}
          onClick={() => setActiveTab('sessions')}
        >
          Chat Sessions ({sessions.length})
        </button>
      </div>

      {/* Cases Overview Table */}
      <div className="bg-white border rounded-xl p-4 shadow-sm">
        <div className="text-sm font-semibold mb-2">Cases Overview</div>
        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-600">
                <th className="px-2 py-1">customer_name</th>
                <th className="px-2 py-1">customer_email</th>
                <th className="px-2 py-1">subject</th>
                <th className="px-2 py-1">category</th>
                <th className="px-2 py-1">priority</th>
                <th className="px-2 py-1">status</th>
                <th className="px-2 py-1">messages</th>
                <th className="px-2 py-1">resolution_summary</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c, i) => (
                <tr key={i} className="border-t">
                  <td className="px-2 py-1">{c.customer_name}</td>
                  <td className="px-2 py-1">{c.customer_email}</td>
                  <td className="px-2 py-1">{c.subject}</td>
                  <td className="px-2 py-1">{c.category}</td>
                  <td className="px-2 py-1">{c.priority}</td>
                  <td className="px-2 py-1">{c.status}</td>
                  <td className="px-2 py-1 text-gray-500">{JSON.stringify(c.messages)?.slice(0, 60)}...</td>
                  <td className="px-2 py-1 text-gray-500">{c.resolution_summary?.slice(0, 60) || 'null'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-2 items-center">
        <input className="border rounded px-2 py-1" placeholder="Search name/email/subject" value={q} onChange={e => setQ(e.target.value)} />
        {activeTab === 'sessions' && (
          <>
            <select className="border rounded px-2 py-1" value={status} onChange={e => setStatus(e.target.value)}>
              <option value="">Status</option>
              <option value="open">open</option>
              <option value="in_progress">in_progress</option>
              <option value="escalated">escalated</option>
              <option value="resolved">resolved</option>
              <option value="closed">closed</option>
            </select>
            <select className="border rounded px-2 py-1" value={prefill} onChange={e => setPrefill(e.target.value)}>
              <option value="all">All</option>
              <option value="with">With prefill</option>
              <option value="without">Without prefill</option>
            </select>
          </>
        )}
        <button className="bg-gray-100 border rounded px-2 py-1" onClick={() => { setQ(''); setStatus(''); load() }}>Reset</button>
      </div>

      {/* Content based on active tab */}
      {activeTab === 'users' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredUsers.map(user => (
            <div key={user.id} className="bg-white border rounded-xl p-4 shadow-sm">
              <div className="flex justify-between items-center">
                <div className="font-medium">{user.email}</div>
                <div className="text-xs text-gray-500">
                  {badge(user.is_admin ? 'Admin' : 'User', user.is_admin ? 'blue' : 'gray')}
                </div>
              </div>
              <div className="text-sm text-gray-600">ID: {user.id}</div>
              <div className="mt-2 text-xs text-gray-400">
                Joined: {user.created_at ? new Date(user.created_at).toLocaleString() : 'Unknown'}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSessions.map(s => (
            <div key={s.session_id} className="bg-white border rounded-xl p-4 shadow-sm">
              <div className="flex justify-between items-center">
                <div className="font-medium">{s.customer_name || s.user_email || s.session_id}</div>
                <div className="text-xs text-gray-500">{badge(s.status, s.status==='escalated' ? 'red' : s.status==='resolved' ? 'green' : 'gray')}</div>
              </div>
              <div className="text-sm text-gray-600">{s.subject} · {s.category}</div>
              <div className="mt-2 text-xs text-gray-500">Last: {s.last_message_role === 'user' ? 'User' : 'AI'} · {s.last_message?.slice(0, 80)}</div>
              <div className="mt-2 text-xs text-gray-400">{s.last_at ? new Date(s.last_at).toLocaleString() : ''}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function badge(text?: string, color = 'gray') {
  return (<span className={`text-xs px-2 py-0.5 rounded bg-${color}-100 text-${color}-700`}>{text}</span>)
}

 
