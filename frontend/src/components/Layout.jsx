import { useState, useRef, useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { LayoutGrid, ClipboardCheck, Users, History, Bell, LogOut, FileText } from 'lucide-react'
import clsx from 'clsx'
import { api } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { relativo } from '../lib/format'

const links = [
  { to: '/', label: 'Painel', icon: LayoutGrid, end: true },
  { to: '/revisao', label: 'Revisão', icon: ClipboardCheck, badge: 'revisao' },
  { to: '/clientes', label: 'Clientes', icon: Users },
  { to: '/historico', label: 'Histórico', icon: History },
]

export default function Layout() {
  const { nome, logout } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: notif } = useQuery({
    queryKey: ['notificacoes'],
    queryFn: () => api.get('/admin/notificacoes').then((r) => r.data),
    refetchInterval: 30_000,
  })
  const { data: dash } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/admin/dashboard').then((r) => r.data),
    refetchInterval: 30_000,
  })

  // quando chega envio novo, o kanban e a fila de revisão também precisam atualizar
  const ultimo = useRef(null)
  useEffect(() => {
    if (!notif) return
    const chave = `${notif.nao_lidas}-${notif.itens[0]?.id}`
    if (ultimo.current && ultimo.current !== chave) {
      qc.invalidateQueries({ queryKey: ['kanban'] })
      qc.invalidateQueries({ queryKey: ['revisao'] })
      qc.invalidateQueries({ queryKey: ['clientes'] })
    }
    ultimo.current = chave
  }, [notif, qc])

  const marcarLidas = useMutation({
    mutationFn: () => api.post('/admin/notificacoes/lidas'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notificacoes'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const [aberto, setAberto] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    const h = (e) => ref.current && !ref.current.contains(e.target) && setAberto(false)
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const naoLidas = notif?.nao_lidas || 0
  const badges = { revisao: dash?.em_analise || 0 }

  return (
    <div className="min-h-screen flex">
      <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-border bg-surface px-3 py-5 sticky top-0 h-screen">
        <div className="flex items-center gap-2 px-2 mb-6">
          <div className="h-8 w-8 rounded-lg bg-accent text-white grid place-items-center">
            <FileText className="h-4 w-4" />
          </div>
          <div>
            <p className="font-bold text-sm leading-tight">Documentos</p>
            <p className="text-[11px] text-muted leading-tight">Contabilidade</p>
          </div>
        </div>
        <nav className="flex flex-col gap-1">
          {links.map(({ to, label, icon: Icon, end, badge }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx('flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition',
                  isActive ? 'bg-accent-soft text-accent' : 'text-muted hover:bg-raised hover:text-primary')
              }
            >
              <Icon className="h-4 w-4" />
              <span className="flex-1">{label}</span>
              {badge && badges[badge] > 0 && (
                <span className="rounded-full bg-accent text-white text-[10px] font-bold px-1.5 py-0.5">{badges[badge]}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto px-2">
          <p className="text-xs text-muted mb-2">Olá, <span className="font-semibold text-primary">{nome}</span></p>
          <button onClick={() => { logout(); navigate('/login') }} className="btn-ghost text-xs px-2 py-1">
            <LogOut className="h-3.5 w-3.5" /> Sair
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-30 bg-surface backdrop-blur border-b border-border px-4 md:px-6 h-14 flex items-center justify-between">
          <div className="md:hidden flex items-center gap-2 font-bold text-sm">
            <div className="h-7 w-7 rounded-lg bg-accent text-white grid place-items-center"><FileText className="h-3.5 w-3.5" /></div>
            Documentos
          </div>
          <div className="hidden md:block text-sm text-muted">
            {dash && (
              <span>
                <b className="text-danger">{dash.atrasadas}</b> atrasadas ·{' '}
                <b className="text-accent">{dash.em_analise}</b> em análise ·{' '}
                <b className="text-primary">{dash.clientes_ativos}</b> clientes
              </span>
            )}
          </div>
          <div className="relative" ref={ref}>
            <button
              onClick={() => { setAberto((v) => !v); if (!aberto && naoLidas) marcarLidas.mutate() }}
              className="relative btn-ghost p-2 rounded-xl"
              aria-label="Notificações"
            >
              <Bell className="h-5 w-5" />
              {naoLidas > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] rounded-full bg-danger text-white text-[10px] font-bold grid place-items-center px-1">
                  {naoLidas}
                </span>
              )}
            </button>
            {aberto && (
              <div className="absolute right-0 mt-2 w-80 max-w-[90vw] card shadow-xl overflow-hidden animate-fade-in">
                <div className="px-4 py-3 border-b border-border font-semibold text-sm">Envios recentes</div>
                <ul className="max-h-96 overflow-y-auto divide-y divide-border">
                  {(notif?.itens || []).length === 0 && <li className="px-4 py-6 text-sm text-muted text-center">Nenhum envio ainda.</li>}
                  {(notif?.itens || []).map((n) => (
                    <li key={n.id}>
                      <button
                        onClick={() => { setAberto(false); navigate('/revisao') }}
                        className={clsx('w-full text-left px-4 py-3 hover:bg-raised', !n.lida_admin && 'bg-accent-soft')}
                      >
                        <p className="text-sm font-semibold truncate">{n.cliente_nome}</p>
                        <p className="text-xs text-muted truncate">{n.descricao}</p>
                        <p className="text-[11px] text-muted mt-0.5">{relativo(n.created_at)}</p>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 px-4 md:px-6 py-5 pb-24 md:pb-8">
          <Outlet />
        </main>

        <nav className="md:hidden fixed bottom-0 inset-x-0 bg-surface border-t border-border flex justify-around px-2 pt-2 pb-[calc(env(safe-area-inset-bottom,0px)+8px)] z-30">
          {links.map(({ to, label, icon: Icon, end, badge }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx('relative flex flex-col items-center gap-0.5 text-[11px] font-medium px-3 py-1 rounded-lg',
                  isActive ? 'text-accent' : 'text-muted')
              }
            >
              <Icon className="h-5 w-5" />
              {label}
              {badge && badges[badge] > 0 && (
                <span className="absolute -top-1 right-0 rounded-full bg-accent text-white text-[9px] font-bold px-1">{badges[badge]}</span>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
