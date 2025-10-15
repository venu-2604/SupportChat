import { useEffect, useState } from 'react'
import { api } from '../../lib/api'

type FAQ = { id?: number, question: string, answer: string }

export default function FAQs() {
  const [items, setItems] = useState<FAQ[]>([])
  const [q, setQ] = useState('')
  const [a, setA] = useState('')
  const [busy, setBusy] = useState(false)
  const hasDraft = q.trim() !== '' || a.trim() !== ''

  const load = async () => {
    const { data } = await api.get('/api/faq', { headers: authHeader() })
    setItems(data)
  }

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    const { data } = await api.post('/api/faq', { question: q, answer: a }, { headers: authHeader() })
    setItems([data, ...items])
    setQ(''); setA('')
  }

  const remove = async (id?: number) => {
    if (!id) return
    await api.delete(`/api/faq/${id}`, { headers: authHeader() })
    setItems(items.filter(i => i.id !== id))
  }

  useEffect(() => { load() }, [])
  
  useEffect(() => {
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      load()
    }, 30000)
    
    return () => clearInterval(interval)
  }, [])

  // Warn about unsaved FAQ inputs
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!hasDraft) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [hasDraft])

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-4">
      <form className="flex gap-2" onSubmit={add}>
        <input className="border rounded px-2 py-1 flex-1" value={q} onChange={e => setQ(e.target.value)} placeholder="Question" />
        <input className="border rounded px-2 py-1 flex-1" value={a} onChange={e => setA(e.target.value)} placeholder="Answer" />
        <button className="bg-green-600 text-white px-3 py-1 rounded shadow">Add</button>
      </form>
      <div>
        <button disabled={busy} className="bg-blue-600 text-white px-3 py-1 rounded shadow" onClick={async () => {
          try {
            setBusy(true)
            await api.post('/api/faq/generate', {}, { headers: authHeader() })
            await load()
          } finally {
            setBusy(false)
          }
        }}>Generate New FAQs</button>
      </div>
      <ul className="space-y-2">
        {items.map(it => (
          <li key={it.id} className="bg-white border rounded p-3 flex justify-between shadow-sm">
            <div>
              <div className="font-medium">{it.question}</div>
              <div className="text-sm text-gray-600">{it.answer}</div>
            </div>
            <button className="text-red-600" onClick={() => remove(it.id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function authHeader() {
  const t = localStorage.getItem('token')
  return t ? { Authorization: `Bearer ${t}` } : {}
}


