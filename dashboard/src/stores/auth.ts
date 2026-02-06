import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const username = ref<string | null>(localStorage.getItem('username'))

  const isAuthenticated = computed(() => !!token.value)

  async function login(user: string, password: string): Promise<boolean> {
    try {
      const response = await api.post('/api/auth/login', {
        username: user,
        password
      })

      if (response.data.token) {
        token.value = response.data.token
        username.value = response.data.username
        
        localStorage.setItem('token', response.data.token)
        localStorage.setItem('username', response.data.username)
        
        api.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`
        
        return true
      }
      
      return false
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  async function checkAuth(): Promise<boolean> {
    if (!token.value) {
      return false
    }

    try {
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
      await api.get('/api/auth/verify')
      return true
    } catch (error) {
      logout()
      return false
    }
  }

  function logout() {
    token.value = null
    username.value = null
    
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    
    delete api.defaults.headers.common['Authorization']
  }

  return {
    token,
    username,
    isAuthenticated,
    login,
    logout,
    checkAuth
  }
})
