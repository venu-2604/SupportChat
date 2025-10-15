import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

export default function Analytics() {
  const [data, setData] = useState<{
    faq_count: number,
    active_tickets: number,
    escalated_count: number,
    resolved_count: number,
    unique_users: number,
    total_sessions: number,
    weekly_tickets: number,
    category_counts: any
  } | null>(null)
  const [userData, setUserData] = useState<{ top_users: Array<{name: string, email: string, tickets: number}> } | null>(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [pageFilter, setPageFilter] = useState('All Pages')
  const [selectedRange, setSelectedRange] = useState('last7')
  const [showCustomPicker, setShowCustomPicker] = useState(false)

  const loadData = async () => {
    const params: any = {}
    if (startDate && endDate) {
      params.start_date = startDate
      params.end_date = endDate
    }

    try {
      Promise.all([
        api.get('/api/admin/analytics', { params, headers: authHeader() }),
        api.get('/api/admin/user-analytics', { params, headers: authHeader() })
      ]).then(([analyticsRes, userRes]) => {
        setData(analyticsRes.data)
        setUserData(userRes.data)
      })
    } catch {
      setData({
        faq_count: 0,
        active_tickets: 0,
        escalated_count: 0,
        resolved_count: 0,
        unique_users: 0,
        total_sessions: 0,
        weekly_tickets: 0,
        category_counts: {}
      })
      setUserData({ top_users: [] })
    }
  }

  useEffect(() => {
    if (selectedRange === 'last7') {
      const end = new Date()
      const start = new Date()
      start.setDate(end.getDate() - 7)
      setStartDate(start.toISOString().split('T')[0])
      setEndDate(end.toISOString().split('T')[0])
    } else if (selectedRange === 'last30') {
      const end = new Date()
      const start = new Date()
      start.setDate(end.getDate() - 30)
      setStartDate(start.toISOString().split('T')[0])
      setEndDate(end.toISOString().split('T')[0])
    } else if (selectedRange === 'last90') {
      const end = new Date()
      const start = new Date()
      start.setDate(end.getDate() - 90)
      setStartDate(start.toISOString().split('T')[0])
      setEndDate(end.toISOString().split('T')[0])
    }
  }, [selectedRange])

  useEffect(() => {
    loadData()
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      loadData()
    }, 30000)
    
    return () => clearInterval(interval)
  }, [startDate, endDate])

  const handleDateRangeChange = (range: string) => {
    setSelectedRange(range)
    setShowCustomPicker(range === 'custom')
  }

  const handleCustomDateApply = () => {
    if (startDate && endDate) {
      loadData()
    }
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-gray-600 mt-1">Manage your app's data</p>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <select 
            value={selectedRange} 
            onChange={e => handleDateRangeChange(e.target.value)}
            className="bg-white border rounded-lg px-4 py-2 shadow-sm"
          >
            <option value="last7">Last 7 days</option>
            <option value="last30">Last 30 days</option>
            <option value="last90">Last 90 days</option>
            <option value="custom">Custom Range</option>
          </select>
          
          {showCustomPicker && (
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
              <span className="text-gray-500">to</span>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
              <button
                onClick={handleCustomDateApply}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700"
              >
                Apply
              </button>
            </div>
          )}
          
          {!showCustomPicker && startDate && endDate && (
            <span className="text-sm text-gray-600">
              {new Date(startDate).toLocaleDateString()} - {new Date(endDate).toLocaleDateString()}
            </span>
          )}
        </div>
        
        <select 
          value={pageFilter} 
          onChange={e => setPageFilter(e.target.value)} 
          className="bg-white border rounded-lg px-4 py-2 shadow-sm"
        >
          <option>All Pages</option>
          <option>Chat</option>
          <option>Cases</option>
          <option>FAQs</option>
        </select>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard label="Total Unique Users" value={data?.unique_users || 0} />
        <StatCard label="Active Cases" value={data?.active_tickets || 0} />
        <StatCard label="Escalated Cases" value={data?.escalated_count || 0} />
        <StatCard label="Resolved Cases" value={data?.resolved_count || 0} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Users */}
        <div className="bg-white border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Top Users</h3>
          <div className="space-y-3">
            {userData?.top_users.length ? 
              userData.top_users.map((user, i) => (
                <div key={i} className="flex justify-between items-center">
                  <span className="text-sm">{user.name || user.email}</span>
                  <span className="text-sm font-medium">{user.tickets} tickets</span>
                </div>
              )) : 
              <div className="text-sm text-gray-500">No users yet</div>
            }
          </div>
        </div>

        {/* Categories */}
        <div className="bg-white border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-2">Support Categories</h3>
          <p className="text-sm text-gray-600 mb-4">Distribution of tickets by category</p>
          <div className="space-y-3">
            {Object.keys(data?.category_counts || {}).length ? 
              Object.entries(data.category_counts).map(([category, count]) => (
                <BarItem 
                  key={category} 
                  label={category || 'Uncategorized'} 
                  value={count as number} 
                  color="bg-teal-600"
                  maxValue={Math.max(...Object.values(data.category_counts))}
                />
              )) :
              <div className="text-sm text-gray-500">No categories yet</div>
            }
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="bg-white border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-2">Recent Activity</h3>
          <p className="text-sm text-gray-600 mb-4">Support activity overview for the selected period</p>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{data?.weekly_tickets || 0}</div>
              <div className="text-sm text-gray-500">New Tickets</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{data?.total_sessions || 0}</div>
              <div className="text-sm text-gray-500">Chat Sessions</div>
            </div>
          </div>
        </div>

        {/* Support Summary */}
        <div className="bg-white border rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-2">Knowledge Base</h3>
          <p className="text-sm text-gray-600 mb-4">Available support resources</p>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm">FAQs Available</span>
              <span className="text-lg font-bold">{data?.faq_count || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Total Unique Users</span>
              <span className="text-lg font-bold">{data?.unique_users || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm">Support Sessions</span>
              <span className="text-lg font-bold">{data?.total_sessions || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Auto-refresh indicator */}
      <div className="text-center">
        <div className="inline-flex items-center gap-2 text-sm text-gray-500">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          Data auto-refreshes every 30 seconds
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string, value: number | string }) {
  return (
    <div className="bg-white border rounded-xl p-4 shadow-sm">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}

function BarItem({ label, value, color, maxValue }: { label: string, value: number, color: string, maxValue?: number }) {
  const max = maxValue || Math.max(value, 1)
  const width = (value / max) * 100
  
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="font-medium">{value}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${width}%` }}></div>
      </div>
    </div>
  )
}

function authHeader() {
  const t = localStorage.getItem('token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}