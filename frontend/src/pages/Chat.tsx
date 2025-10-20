import { useEffect, useRef, useState } from 'react'
import { socket } from '../lib/socket'

type Msg = { role: 'user' | 'assistant', content: string, showResolutionButtons?: boolean, related?: string[], isThinking?: boolean }
type Prefill = { name: string; email: string; subject: string; category: string }

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  // Generate a stable session id once per mount
  const sessionIdRef = useRef<string>(Math.random().toString(36).slice(2))
  const [prefill, setPrefill] = useState<Prefill>({ name: '', email: '', subject: '', category: 'General' })
  const [started, setStarted] = useState(false)
  const DRAFT_KEY = 'chat_draft'

  useEffect(() => {
    // const onBot = (msg: any) => {
    //   const showButtons = msg.content.includes('✅ Does this answer resolve your issue?')
    //   const related = Array.isArray(msg.related) ? msg.related : []
    //   setMessages(m => [...m, { role: 'assistant', content: msg.content, showResolutionButtons: showButtons, related }])
    // }
  
    const onBot = (msg: any) => {
      console.log('🔍 Bot message received:', JSON.stringify(msg, null, 2))
      console.log('🔍 Related field:', msg.related, 'Is Array?', Array.isArray(msg.related), 'Length:', msg.related?.length)
      const showButtons = msg.content.includes('✅ Does this answer resolve your issue?')
      const related = Array.isArray(msg.related) ? msg.related : []
      console.log('🔍 Processed related array:', related, 'Length:', related.length)
      setMessages(m => {
        // Remove any existing "AI is thinking..." messages
        const filteredMessages = m.filter(msg => !msg.isThinking)
        return [...filteredMessages, { role: 'assistant', content: msg.content, showResolutionButtons: showButtons, related }]
      })
    }
    socket.on('bot_message', onBot)
    return () => { socket.off('bot_message', onBot) }
  }, [])

  // Restore draft on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (!raw) return
      const draft = JSON.parse(raw)
      if (draft && typeof draft === 'object') {
        if (draft.sessionId) sessionIdRef.current = draft.sessionId
        if (Array.isArray(draft.messages)) setMessages(draft.messages)
        if (typeof draft.input === 'string') setInput(draft.input)
        if (draft.prefill && typeof draft.prefill === 'object') setPrefill({
          name: draft.prefill.name || '',
          email: draft.prefill.email || '',
          subject: draft.prefill.subject || '',
          category: draft.prefill.category || 'General',
        })
        if (typeof draft.started === 'boolean') setStarted(draft.started)
      }
    } catch {}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Persist draft on changes
  useEffect(() => {
    const payload = {
      sessionId: sessionIdRef.current,
      messages,
      input,
      prefill,
      started,
    }
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(payload))
    } catch {}
  }, [messages, input, prefill, started])

  // Warn on unload if draft exists
  useEffect(() => {
    const hasDraft = started
      ? (messages.length > 0 || input.trim() !== '')
      : (!!prefill.name || !!prefill.email || !!prefill.subject)
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!hasDraft) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [messages, input, prefill, started])

  const begin = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prefill.name || !prefill.email || !prefill.subject) return
    setStarted(true)
    setMessages([{ role: 'assistant', content: `Hello, ${prefill.name}! How can I help you with "${prefill.subject}"?` }])
  }

  const send = (e?: React.FormEvent) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text) return
    setMessages(m => [...m, { role: 'user', content: text }])
    
    // Add "AI is thinking..." message immediately after user message
    setMessages(m => [...m, { role: 'assistant', content: 'AI is thinking...', isThinking: true }])
    
    socket.emit('chat_message', {
      session_id: sessionIdRef.current,
      content: text,
      user_email: prefill.email,
      customer_name: prefill.name,
      subject: prefill.subject,
      category: prefill.category,
    })
    setInput('')
  }

  const sendText = (text: string, isRelatedQuestion: boolean = false) => {
    const t = text.trim()
    if (!t) return
    setMessages(m => [...m, { role: 'user', content: t }])
    
    // Add "AI is thinking..." message immediately after user message
    setMessages(m => [...m, { role: 'assistant', content: 'AI is thinking...', isThinking: true }])
    
    socket.emit('chat_message', {
      session_id: sessionIdRef.current,
      content: t,
      user_email: prefill.email,
      customer_name: prefill.name,
      subject: prefill.subject,
      category: prefill.category,
      is_related_question: isRelatedQuestion,
    })
  }

  const confirmResolution = (confirmed: boolean) => {
    const message = confirmed ? 'Yes, that resolves my issue. Thank you!' : 'No, I still need help with this.'
    setMessages(m => [...m, { role: 'user', content: message }])
    
    // Add "AI is thinking..." message immediately after user message
    setMessages(m => [...m, { role: 'assistant', content: 'AI is thinking...', isThinking: true }])
    
    socket.emit('chat_message', {
      session_id: sessionIdRef.current,
      content: message,
      user_email: prefill.email,
      customer_name: prefill.name,
      subject: prefill.subject,
      category: prefill.category,
    })
  }

  const endChat = () => {
    if (confirm('Are you sure you want to end this chat session? Your conversation will be saved.')) {
      // Clear the draft
      localStorage.removeItem(DRAFT_KEY)
      // Reset state
      setMessages([])
      setInput('')
      setStarted(false)
      // Generate new session ID for next chat
      sessionIdRef.current = Math.random().toString(36).slice(2)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 flex flex-col h-[85vh] gap-4">
      {started && (
        <div className="flex justify-between items-center bg-white border rounded-xl p-4 shadow-sm">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">{prefill.subject}</h2>
            <p className="text-sm text-gray-500">{prefill.name} • {prefill.category}</p>
          </div>
          <button
            onClick={endChat}
            className="text-sm px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            End Chat
          </button>
        </div>
      )}
      {!started && (
        <div className="space-y-6">
          <div className="text-center">
            <div className="mx-auto w-14 h-14 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M7.5 8.25h9m-9 3h6.75m.75 7.5a48.64 48.64 0 0 1-3.75-2.25c-1.188.53-2.49.94-3.9 1.215a.75.75 0 0 1-.87-.735V15a7.5 7.5 0 1 1 8.25 6.75Z"/></svg>
            </div>
            <h1 className="mt-4 text-3xl font-bold tracking-tight">Customer Support Chat</h1>
            <p className="mt-1 text-gray-600">Get instant help from our AI-powered support assistant</p>
          </div>

          <form className="bg-white border rounded-2xl p-6 shadow-sm space-y-4" onSubmit={begin}>
            <div className="flex items-center gap-2 text-lg font-semibold">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-blue-600"><path d="M12 3c-3.866 0-7 3.134-7 7 0 2.761 1.548 5.166 3.813 6.348A8.962 8.962 0 0 0 3 21a9 9 0 1 0 18 0 8.962 8.962 0 0 0-5.813-4.652C17.452 15.166 19 12.761 19 10c0-3.866-3.134-7-7-7Z"/></svg>
              Start Your Support Session
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <span className="inline-flex w-4">👤</span> Your Name *
                </label>
                <input className="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500" placeholder="Enter your name" value={prefill.name} onChange={e => setPrefill({ ...prefill, name: e.target.value })} />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <span className="inline-flex w-4">✉️</span> Email Address
                </label>
                <input type="email" className="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500" placeholder="your.email@example.com" value={prefill.email} onChange={e => setPrefill({ ...prefill, email: e.target.value })} />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <span className="inline-flex w-4">📝</span> What can we help you with? *
              </label>
              <input className="mt-1 w-full border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500" placeholder="Briefly describe your issue" value={prefill.subject} onChange={e => setPrefill({ ...prefill, subject: e.target.value })} />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Category</label>
              <select className="mt-1 w-full border rounded-lg px-3 py-2" value={prefill.category} onChange={e => setPrefill({ ...prefill, category: e.target.value })}>
                <option>General Question</option>
                <option>Technical</option>
                <option>Billing</option>
                <option>Account</option>
              </select>
            </div>

            <button className="w-full bg-gradient-to-r from-blue-500 to-indigo-500 text-white px-4 py-3 rounded-xl shadow flex items-center justify-center gap-2">
              <span>📨</span> Start Chat Session
            </button>
          </form>
        </div>
      )}
      <div className="bg-white border rounded-xl p-6 overflow-auto space-y-4 shadow-sm flex-1">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <div className="mx-auto w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <div className="text-lg font-medium">Welcome to Customer Support!</div>
            <div className="text-sm">Ask any question and our AI assistant will help you.</div>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div className={`max-w-[80%] ${m.role === 'user' ? 'order-2' : 'order-1'}`}>
              <div className={`inline-flex items-start gap-2 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                  m.role === 'user' 
                    ? 'bg-blue-600 text-white order-2' 
                    : 'bg-gray-200 text-gray-700 order-1'
                }`}>
                  {m.role === 'user' ? 'U' : 'AI'}
                </div>
                <div className={`px-4 py-3 rounded-2xl shadow-sm ${m.role === 'user' 
                  ? 'bg-blue-600 text-white order-1' 
                  : 'bg-gray-100 text-gray-900 order-2'
                }`}>
                  <div className="whitespace-pre-wrap flex items-center gap-2">
                    {m.content}
                    {m.isThinking && (
                      <span className="text-gray-500 text-sm">🌙</span>
                    )}
                  </div>
                  {m.related && m.related.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-semibold text-gray-600 mb-2">Related questions:</div>
                      <div className="flex flex-wrap gap-2">
                        {m.related.map((q, idx) => (
                          <button
                            key={idx}
                            onClick={() => sendText(q)}
                            className="text-xs px-3 py-1.5 rounded-lg border bg-white border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-blue-400 transition-colors"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {m.showResolutionButtons && (
                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => confirmResolution(true)}
                        className="bg-green-600 text-white px-3 py-1 rounded-lg text-sm hover:bg-green-700 transition-colors"
                      >
                        ✅ Yes, Resolved
                      </button>
                      <button
                        onClick={() => confirmResolution(false)}
                        className="bg-gray-500 text-white px-3 py-1 rounded-lg text-sm hover:bg-gray-600 transition-colors"
                      >
                        ❌ Still Need Help
                      </button>
                    </div>
                  )}
                  <div className={`text-xs mt-1 ${m.role === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                    {new Date().toLocaleTimeString([], { hour: '2-digit', minutes: '2-digit' })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <form className="bg-white border rounded-xl p-4 shadow-sm" onSubmit={send}>
        <div className="flex gap-3">
          <input 
            className="flex-1 border rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
            value={input} 
            onChange={e => setInput(e.target.value)} 
            placeholder="Type your message..." 
          />
          <button 
            type="submit" 
            disabled={!input.trim()}
            className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3 rounded-xl shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <span>Send</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  )
}