import { useState } from 'react'
import { api } from '../lib/api'
import { useNavigate, Link } from 'react-router-dom'
import { useEffect } from 'react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const body = new URLSearchParams()
      body.set('username', email)
      body.set('password', password)
      const { data } = await api.post('/api/auth/login', body, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      localStorage.setItem('token', data.access_token)
      navigate('/admin')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Login failed')
    }
  }

  // Warn on unload if inputs are non-empty
  useEffect(() => {
    const hasDraft = email.trim() !== '' || password.trim() !== ''
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!hasDraft) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [email, password])

  return (
    <div className="max-w-sm mx-auto bg-white border rounded p-4">
      <div className="text-lg font-semibold mb-3">Admin Login</div>
      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
      <form className="space-y-2" onSubmit={submit}>
        <input className="w-full border rounded px-3 py-2" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
        <input type="password" className="w-full border rounded px-3 py-2" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
        <button className="w-full bg-blue-600 text-white rounded px-3 py-2">Login</button>
      </form>
      <div className="text-sm mt-2">No account? <Link className="text-blue-600" to="/register">Register</Link></div>
    </div>
  )
}


