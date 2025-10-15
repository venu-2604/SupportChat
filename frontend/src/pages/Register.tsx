import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useNavigate, Link } from 'react-router-dom'

export default function Register() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/api/auth/register', { email, password })
      localStorage.setItem('token', data.access_token)
      navigate('/admin')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Register failed')
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
      <div className="text-lg font-semibold mb-3">Register</div>
      {error && <div className="text-red-600 text-sm mb-2">{error}</div>}
      <form className="space-y-2" onSubmit={submit}>
        <input className="w-full border rounded px-3 py-2" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} />
        <input type="password" className="w-full border rounded px-3 py-2" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
        <button className="w-full bg-blue-600 text-white rounded px-3 py-2">Create account</button>
      </form>
      <div className="text-sm mt-2">Have an account? <Link className="text-blue-600" to="/login">Login</Link></div>
    </div>
  )
}


