import axios from 'axios'
import { authStorage } from '../context/AuthContext'

const DEFAULT_API_BASE = '/api/v1'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE,
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = authStorage.getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isUnauthorized = error.response && error.response.status === 401
    if (isUnauthorized) {
      authStorage.clear()
      const url = error.config && error.config.url ? error.config.url : ''
      if (!url.includes('/auth/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (username, password) => {
    const formData = new URLSearchParams()
    formData.append('username', String(username ?? '').trim())
    formData.append('password', String(password ?? '').trim())
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  me: () => api.get('/auth/me'),
}

export const laptopApi = {
  getAll: (params) => api.get('/laptops/', { params }),
  getById: (id) => api.get(`/laptops/${id}`),
  create: (data) => api.post('/laptops/', data),
  update: (id, data) => api.put(`/laptops/${id}`, data),
  updateStatus: (id, status) => api.put(`/laptops/${id}/status`, { status }),
  deactivate: (id) => api.put(`/laptops/${id}/deactivate`),
  activate: (id) => api.put(`/laptops/${id}/activate`),
}

export const internApi = {
  getAll: (params) => api.get('/interns/', { params }),
  getById: (id) => api.get(`/interns/${id}`),
  create: (data) => api.post('/interns/', data),
  update: (id, data) => api.put(`/interns/${id}`, data),
  delete: (id) => api.delete(`/interns/${id}`),
  getBatchSummary: () => api.get('/interns/summary'),
}

export const allocationApi = {
  getAll: (params) => api.get('/allocations/', { params }),
  getById: (id) => api.get(`/allocations/${id}`),
  getActive: () => api.get('/allocations/active'),
  getAvailableLaptops: () => api.get('/allocations/available-laptops'),
  getAllocatableInterns: () => api.get('/allocations/allocatable-interns'),
  create: (data) => api.post('/allocations/', data),
  returnLaptop: (id) => api.put(`/allocations/${id}/return`),
  cancel: (id) => api.put(`/allocations/${id}/cancel`),
  getHistory: (params) => api.get('/allocations/history', { params }),
  getReports: (params) => api.get('/allocations/reports', { params }),
  exportCsv: (params) =>
    api.get('/allocations/export', { params, responseType: 'blob' }),
}

export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats'),
}

export const excelApi = {
  importExcel: (file, onProgress, signal) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/import/excel', formData, {
      signal,
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    })
  },
  exportExcel: () => api.get('/export/excel', { responseType: 'blob' }),
  downloadTemplate: () => api.get('/export/template', { responseType: 'blob' }),
}

export const getErrorMessage = (error) => {
  if (error.response && error.response.data && error.response.data.detail) {
    const detail = error.response.data.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg).join('; ')
    }
  }
  return error.message || 'An error occurred'
}

export default api
