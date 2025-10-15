import axios from 'axios'

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE
  || (import.meta.env.PROD ? 'https://supportchat-j0ja.onrender.com' : 'http://localhost:8000')

export const api = axios.create({
  baseURL: DEFAULT_API_BASE,
  withCredentials: false,
})

// Add request interceptor to include auth token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, error => {
  return Promise.reject(error)
})


