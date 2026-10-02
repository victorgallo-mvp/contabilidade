import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search, ChevronRight } from 'lucide-react'
import { api } from '../api/client'
import { Carregando, Vazio, Badge } from '../components/ui'
import ClienteForm from '../components/ClienteForm'

export default function Clientes() {
  const [busca, setBusca] = useState('')
  const [novo, setNovo] = useState(false)
  const { data, isLoading } = useQuery({ queryKey: ['clientes'], queryFn: () => api.get('/admin/clientes').then((r) => r.data) })

  const lista = (data || []).filter((c) => c.nome.toLowerCase().includes(busca.toLowerCase()) || (c.responsavel || '').toLowerCase().includes(busca.toLowerCase()))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">Clientes</h1>
          <p className="text-sm text-muted">{data?.length || 0} ativos. Cada um tem seu link fixo do portal.</p>
        </div>
        <button className="btn-primary w-full sm:w-auto" onClick={() => setNovo(true)}><Plus className="h-4 w-4" /> Novo cliente</button>
      </div>

      <div className="relative max-w-sm">
        <Search className="h-4 w-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
        <input className="input pl-9" placeholder="Buscar por nome ou responsável" value={busca} onChange={(e) => setBusca(e.target.value)} />
      </div>

      {isLoading ? <Carregando /> : !lista.length ? (
        <Vazio titulo="Nenhum cliente" texto="Cadastre o primeiro cliente para gerar o link do portal." />
      ) : (
        <div className="card overflow-hidden">
          <ul className="divide-y divide-border">
            {lista.map((c) => (
              <li key={c.id}>
                <Link to={`/clientes/${c.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-raised transition">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-sm truncate">{c.nome}</p>
                    <p className="text-xs text-muted truncate">{c.responsavel || '—'} · {c.whatsapp || 'sem WhatsApp'} · {c.contas.length} conta(s)</p>
                  </div>
                  <div className="flex flex-col sm:flex-row items-end sm:items-center gap-1 shrink-0">
                    {c.atrasadas > 0 && <Badge className="bg-danger-soft text-danger">{c.atrasadas} atrasada(s)</Badge>}
                    {c.em_analise > 0 && <Badge className="bg-accent-soft text-accent">{c.em_analise} em análise</Badge>}
                    {c.atrasadas === 0 && c.em_analise === 0 && <Badge className="bg-success-soft text-success">em dia</Badge>}
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {novo && <ClienteForm onFechar={() => setNovo(false)} />}
    </div>
  )
}
