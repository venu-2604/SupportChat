import { io } from 'socket.io-client'

const DEFAULT_SOCKET_URL = import.meta.env.VITE_SOCKET_URL
  || (import.meta.env.PROD ? 'https://supportchat-j0ja.onrender.com' : 'http://localhost:8000')

export const socket = io(DEFAULT_SOCKET_URL, {
  autoConnect: true,
  // Let the client negotiate transport (polling -> websocket upgrade) for broader compatibility
  // Explicitly set the default Socket.IO path
  path: '/socket.io',
})


