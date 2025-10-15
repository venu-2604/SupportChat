import { io } from 'socket.io-client'

const DEFAULT_SOCKET_URL = import.meta.env.VITE_SOCKET_URL
  || (import.meta.env.PROD ? 'https://supportchat-j0ja.onrender.com' : 'http://localhost:8000')

export const socket = io(DEFAULT_SOCKET_URL, {
  autoConnect: true,
  // Force websocket to avoid proxy issues with long-polling upgrades in production
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 10,
  reconnectionDelay: 500,
  reconnectionDelayMax: 2000,
  timeout: 20000,
  // Explicitly set the default Socket.IO path
  path: '/socket.io',
})

// Expose for debugging in browser console
// @ts-ignore
if (typeof window !== 'undefined') (window as any).socket = socket

// Verbose client-side logging for diagnostics in production
socket.on('connect', () => console.log('🔗 socket connected:', socket.id))
socket.on('disconnect', (reason) => console.log('❌ socket disconnected:', reason))
socket.on('connect_error', (err) => console.log('⚠️ socket connect_error:', err?.message || err))
socket.onAny((event, ...args) => {
  try {
    console.log('📨 socket event:', event, JSON.stringify(args?.[0] ?? null))
  } catch {
    console.log('📨 socket event:', event, args)
  }
})


