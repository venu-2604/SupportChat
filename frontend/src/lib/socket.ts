import { io } from 'socket.io-client'

export const socket = io(import.meta.env.VITE_SOCKET_URL || 'http://localhost:8000', {
  autoConnect: true,
  // Let the client negotiate transport (polling -> websocket upgrade) for broader compatibility
  // Explicitly set the default Socket.IO path
  path: '/socket.io',
})


