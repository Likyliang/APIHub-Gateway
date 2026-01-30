import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    const { data } = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return data
  },
  register: async (username: string, email: string, password: string) => {
    const { data } = await api.post('/auth/register', { username, email, password })
    return data
  },
  getMe: async () => {
    const { data } = await api.get('/auth/me')
    return data
  },
}

// API Keys API
export const keysApi = {
  list: async () => {
    const { data } = await api.get('/keys')
    return data
  },
  create: async (keyData: {
    name: string
    description?: string
    rate_limit?: number
    quota_limit?: number
  }) => {
    const { data } = await api.post('/keys', keyData)
    return data
  },
  update: async (keyId: number, keyData: {
    name?: string
    description?: string
    rate_limit?: number
    is_active?: boolean
  }) => {
    const { data } = await api.put(`/keys/${keyId}`, keyData)
    return data
  },
  delete: async (keyId: number) => {
    await api.delete(`/keys/${keyId}`)
  },
}

// Usage API
export const usageApi = {
  getStats: async (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams()
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    const { data } = await api.get(`/usage/stats?${params}`)
    return data
  },
  getRecords: async (limit = 100) => {
    const { data } = await api.get(`/usage/records?limit=${limit}`)
    return data
  },
  getDaily: async (days = 30) => {
    const { data } = await api.get(`/usage/daily?days=${days}`)
    return data
  },
  getModels: async (startDate?: string, endDate?: string) => {
    const params = new URLSearchParams()
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    const { data } = await api.get(`/usage/models?${params}`)
    return data
  },
  getQuota: async () => {
    const { data } = await api.get('/usage/quota')
    return data
  },
}

// Users API (Admin)
export const usersApi = {
  list: async () => {
    const { data } = await api.get('/users')
    return data
  },
  create: async (userData: {
    username: string
    email: string
    password: string
    is_admin?: boolean
    quota_limit?: number
  }) => {
    const { data } = await api.post('/users', userData)
    return data
  },
  update: async (userId: number, userData: {
    email?: string
    is_active?: boolean
    is_admin?: boolean
    quota_limit?: number
  }) => {
    const { data } = await api.put(`/users/${userId}`, userData)
    return data
  },
  delete: async (userId: number) => {
    await api.delete(`/users/${userId}`)
  },
  resetQuota: async (userId: number) => {
    const { data } = await api.post(`/users/${userId}/reset-quota`)
    return data
  },
}

// Payment API
export const paymentApi = {
  getPlans: async () => {
    const { data } = await api.get('/payment/plans')
    return data
  },
  createOrder: async (planId: number, method: string) => {
    const { data } = await api.post('/payment/order', { plan_id: planId, method })
    return data
  },
  getOrderStatus: async (orderNo: string) => {
    const { data } = await api.get(`/payment/order/${orderNo}`)
    return data
  },
  getHistory: async () => {
    const { data } = await api.get('/payment/history')
    return data
  },
  // Admin
  getStats: async () => {
    const { data } = await api.get('/payment/admin/stats')
    return data
  },
  createPlan: async (planData: {
    name: string
    price: number
    quota_amount: number
    description?: string
    is_popular?: boolean
  }) => {
    const { data } = await api.post('/payment/admin/plans', planData)
    return data
  },
}

export default api
