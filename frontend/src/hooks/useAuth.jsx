import { createContext, useContext, useState } from 'react'
import { api } from '../api/client'

const Ctx = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [nome, setNome] = useState(() => localStorage.getItem('nome') || '')

  async function login(username, password) {
    const form = new URLSearchParams({ username, password })
    const { data } = await api.post('/auth/login', form)
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('nome', data.nome)
    setToken(data.access_token)
    setNome(data.nome)
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('nome')
    setToken(null)
    setNome('')
  }

  return <Ctx.Provider value={{ token, nome, login, logout, logado: !!token }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
