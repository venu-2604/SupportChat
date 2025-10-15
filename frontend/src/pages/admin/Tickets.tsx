import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

type Ticket = { id?: number, user_email: string, customer_name?: string, subject: string, category?: string, description: string, status?: string, priority?: string, session_id?: string, created_at?: string }
type ChatSession = { session_id: string, customer_name: string, user_email: string, subject: string, category: string, message_count: number, created_at: string, updated_at: string, is_escalated: boolean, ticket_id?: number, ticket_status?: string }

export default function Tickets() {
  const [items, setItems] = useState<Ticket[]>([])
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [activeTab, setActiveTab] = useState<'tickets' | 'sessions'>('sessions')
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [category, setCategory] = useState('')
  const [priority, setPriority] = useState('')
  const [view, setView] = useState<Ticket | null>(null)
  const [resolutionStats, setResolutionStats] = useState<any>(null)

  const load = async () => {
    try {
      const params: any = {}
      if (q) params.q = q
      if (status) params.status = status
      if (category) params.category = category
      if (priority) params.priority = priority
      const { data } = await api.get('/api/tickets', { params, headers: authHeader() })
      setItems(data)
    } catch (error) {
      console.error('Failed to load tickets:', error)
    }
  }

  const loadResolutionStats = async () => {
    try {
      const { data } = await api.get('/api/tickets/resolution-stats', { headers: authHeader() })
      setResolutionStats(data)
    } catch (error) {
      console.error('Failed to load resolution stats:', error)
    }
  }

  const loadChatSessions = async () => {
    try {
      const params: any = {}
      if (q) params.q = q
      const { data } = await api.get('/api/chat-sessions', { params, headers: authHeader() })
      setChatSessions(data)
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
    }
  }

  useEffect(() => { 
    if (activeTab === 'tickets') {
      load()
      loadResolutionStats()
    } else {
      loadChatSessions()
    }
  }, [q, status, category, priority, activeTab])
  
  useEffect(() => {
    // Auto-refresh every 10 seconds for real-time updates
    const interval = setInterval(() => {
      if (activeTab === 'tickets') {
        load()
        loadResolutionStats()
      } else {
        loadChatSessions()
      }
    }, 10000)
    
    return () => clearInterval(interval)
  }, [q, status, category, priority])

  const badge = (text?: string, color = 'gray') => (
    <span className={`text-xs px-2 py-0.5 rounded bg-${color}-100 text-${color}-700`}>{text}</span>
  )

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-5">
      {/* Stats row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Total Cases" value={items.length} icon={<IconFolder/>} />
        <StatCard label="Active Cases" value={items.filter(i => i.status === 'open' || i.status === 'in_progress' || i.status === 'escalated').length} icon={<IconClock/>} />
        <StatCard label="Escalated" value={items.filter(i => i.status === 'escalated').length} icon={<IconWarn/>} />
        <StatCard label="Resolved" value={items.filter(i => i.status === 'resolved').length} icon={<IconUp/>} />
      </div>

      {/* Resolution Statistics */}
      {resolutionStats && (
        <div className="bg-white border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span>📊</span> Resolution Analytics
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">{resolutionStats.resolution_rate}%</div>
              <div className="text-sm text-gray-600">Resolution Rate</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">{resolutionStats.avg_resolution_hours}h</div>
              <div className="text-sm text-gray-600">Avg Resolution Time</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-purple-600">{resolutionStats.resolved_tickets}</div>
              <div className="text-sm text-gray-600">Total Resolved</div>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white border rounded p-4 grid grid-cols-1 md:grid-cols-5 gap-3 shadow-sm">
        <input className="border rounded px-2 py-1" placeholder="Search name/email/subject" value={q} onChange={e => setQ(e.target.value)} />
        <select className="border rounded px-2 py-1" value={status} onChange={e => setStatus(e.target.value)}>
          <option value="">Status</option>
          <option>open</option>
          <option>in_progress</option>
          <option>escalated</option>
          <option>resolved</option>
          <option>closed</option>
        </select>
        <select className="border rounded px-2 py-1" value={category} onChange={e => setCategory(e.target.value)}>
          <option value="">Category</option>
          <option>General</option>
          <option>Technical</option>
          <option>Billing</option>
          <option>Account</option>
        </select>
        <select className="border rounded px-2 py-1" value={priority} onChange={e => setPriority(e.target.value)}>
          <option value="">Priority</option>
          <option>low</option>
          <option>medium</option>
          <option>high</option>
          <option>urgent</option>
        </select>
        <button className="bg-gray-100 border rounded px-2 py-1" onClick={() => { setQ(''); setStatus(''); setCategory(''); setPriority('') }}>Reset</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {items.map(t => (
          <div key={t.id} className="bg-white border rounded-xl p-4 shadow-sm">
            <div className="flex justify-between">
              <div className="font-medium">{t.subject}</div>
              <div className="space-x-1">
                {badge(t.status, t.status === 'escalated' ? 'red' : t.status === 'resolved' ? 'green' : 'gray')}
                {badge(t.priority, t.priority === 'high' || t.priority === 'urgent' ? 'red' : 'gray')}
              </div>
            </div>
            <div className="text-sm text-gray-600">{t.description}</div>
            <div className="text-xs text-gray-500">{t.customer_name} · {t.user_email} · {t.category}</div>
            <div className="mt-2 flex items-center justify-between">
              <div className="text-xs text-gray-400">{t.created_at ? new Date(t.created_at).toLocaleDateString() : ''}</div>
              <button className="text-blue-600" onClick={() => setView(t)}>View Details</button>
            </div>
          </div>
        ))}
      </div>

      {view && (
        <CaseModal ticket={view} onClose={() => setView(null)} />
      )}
    </div>
  )
}

function StatCard({ label, value, icon }: { label: string, value: number, icon: React.ReactNode }) {
  return (
    <div className="bg-white border rounded-xl p-4 shadow-sm flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">{icon}</div>
      <div>
        <div className="text-sm text-gray-500">{label}</div>
        <div className="text-2xl font-semibold">{value}</div>
      </div>
    </div>
  )
}

function IconFolder() { return (<span role="img" aria-label="folder">📁</span>) }
function IconClock() { return (<span role="img" aria-label="clock">🕒</span>) }
function IconWarn() { return (<span role="img" aria-label="warn">⚠️</span>) }
function IconUp() { return (<span role="img" aria-label="up">📈</span>) }

function CaseModal({ ticket, onClose }: { ticket: Ticket, onClose: () => void }) {
  const [history, setHistory] = useState<{ role: string, content: string }[]>([])
  const [newStatus, setNewStatus] = useState(ticket.status || 'open')
  const [isUpdating, setIsUpdating] = useState(false)
  
  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await api.get('/api/admin/chats', { headers: authHeader() })
        const filtered = data.filter((d: any) => d.session_id === ticket.session_id)
        setHistory(filtered)
      } catch { }
    }
    load()
  }, [ticket.session_id])

  const updateStatus = async () => {
    if (newStatus === ticket.status) return
    
    setIsUpdating(true)
    try {
      await api.patch(`/api/tickets/${ticket.id}`, 
        { status: newStatus }, 
        { headers: authHeader() }
      )
      // Update local state and close modal
      ticket.status = newStatus
      setIsUpdating(false)
      alert('Status updated successfully!')
      onClose()
      // Parent component will auto-refresh via interval
    } catch (error) {
      console.error('Failed to update status:', error)
      alert('Failed to update status. Please try again.')
      setIsUpdating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl rounded shadow p-5 space-y-3">
        <div className="flex justify-between items-center">
          <div className="font-semibold">Case #{ticket.id} · {ticket.subject}</div>
          <button onClick={onClose}>Close</button>
        </div>
        
        {/* Status Update Section */}
        <div className="bg-gray-50 p-4 rounded-lg space-y-3">
          <div className="flex items-center gap-3">
            <label className="font-medium">Status:</label>
            <select 
              value={newStatus} 
              onChange={(e) => setNewStatus(e.target.value)}
              className="border rounded px-2 py-1"
            >
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="escalated">Escalated</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
            <button
              onClick={updateStatus}
              disabled={isUpdating || newStatus === ticket.status}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
            >
              {isUpdating ? 'Updating...' : 'Update Status'}
            </button>
          </div>
          <div className="text-sm text-gray-600">
            <strong>Customer:</strong> {ticket.customer_name} ({ticket.user_email})<br/>
            <strong>Category:</strong> {ticket.category}<br/>
            <strong>Priority:</strong> {ticket.priority}<br/>
            <strong>Created:</strong> {ticket.created_at ? new Date(ticket.created_at).toLocaleString() : 'N/A'}
          </div>
        </div>

        <div className="max-h-96 overflow-auto space-y-2">
          {history.map((h, i) => (
            <div key={i} className={h.role === 'user' ? 'text-right' : 'text-left'}>
              <span className={h.role === 'user' ? 'bg-blue-600 text-white px-3 py-2 rounded inline-block' : 'bg-gray-200 px-3 py-2 rounded inline-block'}>
                {h.content}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function authHeader() {
  const t = localStorage.getItem('token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}


