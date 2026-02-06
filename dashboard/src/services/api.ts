import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.DEV ? '' : window.location.origin,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API functions
export async function getStatus() {
  const response = await api.get('/api/status')
  return response.data
}

export async function getConfig() {
  const response = await api.get('/api/config')
  return response.data
}

export async function updateConfig(data: Record<string, any>) {
  const response = await api.put('/api/config', data)
  return response.data
}

export async function getProviders() {
  const response = await api.get('/api/providers')
  return response.data
}

export async function getPlatforms() {
  const response = await api.get('/api/platforms')
  return response.data
}

export async function getPlugins() {
  const response = await api.get('/api/plugins')
  return response.data
}

export async function reloadPlugin(name: string) {
  const response = await api.post(`/api/plugins/${name}/reload`)
  return response.data
}

export async function getTools() {
  const response = await api.get('/api/tools')
  return response.data
}

export async function getLogs(count: number = 100) {
  const response = await api.get('/api/logs', { params: { count } })
  return response.data
}
