import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { toast } from 'sonner'
import { useAuth } from '../hooks/useAuth'
import { erroMsg } from '../api/client'

export default function Login() {
  const { login, logado } = useAuth()
  const navigate = useNavigate()
  const [u, setU] = useState('')
  const [p, setP] = useState('')
  const [carregando, setCarregando] = useState(false)

  if (logado) return <Navigate to="/" replace />

  async function enviar(e) {
    e.preventDefault()
    setCarregando(true)
    try {
      await login(u.trim().toLowerCase(), p)
      navigate('/')
    } catch (err) {
      toast.error(erroMsg(err, 'Não foi possível entrar'))
    } finally {
      setCarregando(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <form onSubmit={enviar} className="card w-full max-w-sm p-6 space-y-4 animate-fade-in">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-accent text-white grid place-items-center"><FileText className="h-5 w-5" /></div>
          <div>
            <h1 className="font-bold">Gestão de documentos</h1>
            <p className="text-xs text-muted">Acesso do escritório</p>
          </div>
        </div>
        <div>
          <label className="label">Usuário</label>
          <input className="input" value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" autoFocus />
        </div>
        <div>
          <label className="label">Senha</label>
          <input className="input" type="password" value={p} onChange={(e) => setP(e.target.value)} autoComplete="current-password" />
        </div>
        <button className="btn-primary w-full" disabled={carregando || !u || !p}>
          {carregando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  )
}
