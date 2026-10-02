import axios from 'axios'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !err.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('token')
      localStorage.removeItem('nome')
      if (!window.location.pathname.startsWith('/c/') && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

export function erroMsg(err, fallback = 'Algo deu errado') {
  const d = err?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).join('; ')
  return err?.message || fallback
}

// abre um arquivo protegido em nova aba (o token vai no header, então baixamos como blob)
export async function abrirArquivo(url) {
  const r = await api.get(url, { responseType: 'blob' })
  const blobUrl = URL.createObjectURL(r.data)
  window.open(blobUrl, '_blank', 'noopener')
  setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000)
}

export async function baixarArquivo(url, nome) {
  const r = await api.get(url, { responseType: 'blob' })
  const blobUrl = URL.createObjectURL(r.data)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = nome
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000)
}
