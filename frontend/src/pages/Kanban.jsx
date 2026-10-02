import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { MessageCircle, Paperclip, ChevronDown, ChevronUp, ExternalLink, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'
import { api } from '../api/client'
import { Carregando, SituacaoBadge, Stat, Vazio } from '../components/ui'
import CobrancaModal from '../components/CobrancaModal'
import UploadAdminModal from '../components/UploadAdminModal'
import { competenciaRotulo, dataCurta, relativo } from '../lib/format'

const COLUNAS = [
  { key: 'atrasado', titulo: 'Atrasados', cor: 'border-t-danger', tom: 'text-danger' },
  { key: 'em_analise', titulo: 'Em análise', cor: 'border-t-accent', tom: 'text-accent' },
  { key: 'aguardando', titulo: 'Aguardando prazo', cor: 'border-t-info', tom: 'text-info' },
  { key: 'concluido', titulo: 'Concluídos', cor: 'border-t-success', tom: 'text-success' },
]

export default function Kanban() {
  const [competencia, setCompetencia] = useState('todas')
  const [cobrar, setCobrar] = useState(null)
  const [anexar, setAnexar] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['kanban', competencia],
    queryFn: () => api.get('/admin/kanban', { params: { competencia } }).then((r) => r.data),
    refetchInterval: 30_000,
  })
  const { data: dash } = useQuery({ queryKey: ['dashboard'], queryFn: () => api.get('/admin/dashboard').then((r) => r.data) })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">Painel de documentos</h1>
          <p className="text-sm text-muted">Cada card é um cliente em um mês. Clique para ver o que falta.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-muted">Competência</label>
          <select className="input w-auto" value={competencia} onChange={(e) => setCompetencia(e.target.value)}>
            <option value="todas">Todas</option>
            {(data?.competencias || []).map((c) => <option key={c} value={c}>{competenciaRotulo(c)}</option>)}
          </select>
        </div>
      </div>

      {dash && (
        <div className="flex flex-wrap gap-3">
          <Stat rotulo="Clientes com atraso" valor={dash.clientes_com_atraso} tom="text-danger" />
          <Stat rotulo="Pendências atrasadas" valor={dash.atrasadas} tom="text-danger" />
          <Stat rotulo="Aguardando revisão" valor={dash.em_analise} tom="text-accent" />
          <Stat rotulo="Aceitas no mês" valor={dash.aceitas_mes} tom="text-success" />
        </div>
      )}

      {isLoading ? <Carregando /> : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {COLUNAS.map((col) => {
            const cards = data?.colunas?.[col.key] || []
            return (
              <section key={col.key} className={clsx('card border-t-4 p-3 min-h-[200px]', col.cor)}>
                <header className="flex items-center justify-between px-1 pb-2">
                  <h2 className={clsx('font-bold text-sm', col.tom)}>{col.titulo}</h2>
                  <span className="text-xs font-semibold text-muted bg-raised rounded-full px-2 py-0.5">{cards.length}</span>
                </header>
                <div className="space-y-2">
                  {cards.length === 0 && <p className="text-xs text-muted text-center py-6">Nada aqui.</p>}
                  {cards.map((c) => (
                    <Card key={`${c.cliente_id}-${c.competencia}`} card={c} onCobrar={() => setCobrar(c)} onAnexar={() => setAnexar(c)} />
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      )}

      <CobrancaModal card={cobrar} onFechar={() => setCobrar(null)} />
      {anexar && (
        <UploadAdminModal
          clienteId={anexar.cliente_id}
          clienteNome={anexar.cliente_nome}
          obrigacoes={anexar.obrigacoes}
          onFechar={() => setAnexar(null)}
        />
      )}
    </div>
  )
}

function Card({ card, onCobrar, onAnexar }) {
  const [aberto, setAberto] = useState(false)
  const podeCobrar = card.coluna === 'atrasado' || card.coluna === 'aguardando'
  const temAlerta = card.obrigacoes.some((o) => o.documentos?.some((d) => d.ia_status === 'alerta' && d.status === 'em_analise'))
  return (
    <article className="rounded-xl border border-border bg-surface p-3 animate-fade-in">
      <button className="w-full text-left" onClick={() => setAberto((v) => !v)}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="font-semibold text-sm truncate">{card.cliente_nome}</p>
            <p className="text-xs text-muted">{card.competencia_rotulo} · vence {dataCurta(card.vencimento)}</p>
          </div>
          {aberto ? <ChevronUp className="h-4 w-4 text-muted shrink-0" /> : <ChevronDown className="h-4 w-4 text-muted shrink-0" />}
        </div>
        <div className="flex flex-wrap gap-1 mt-2">
          {card.dias_atraso > 0 && card.coluna === 'atrasado' && (
            <span className="text-[11px] font-semibold text-danger">{card.dias_atraso} dias de atraso</span>
          )}
          {card.total_cobrancas > 0 && (
            <span className="text-[11px] text-muted">· cobrado {card.total_cobrancas}x, última {relativo(card.ultima_cobranca)}</span>
          )}
          {temAlerta && <span className="text-[11px] text-warning inline-flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> alerta da leitura</span>}
        </div>
      </button>

      {aberto && (
        <div className="mt-3 space-y-2">
          <ul className="space-y-1">
            {card.obrigacoes.map((o) => (
              <li key={o.id} className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate">{o.descricao}</span>
                <SituacaoBadge situacao={o.situacao} />
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {podeCobrar && (
              <button className="btn-whats text-xs px-3 py-1.5" onClick={onCobrar}>
                <MessageCircle className="h-3.5 w-3.5" /> Cobrar
              </button>
            )}
            {card.coluna !== 'concluido' && (
              <button className="btn-secondary text-xs px-3 py-1.5" onClick={onAnexar}>
                <Paperclip className="h-3.5 w-3.5" /> Anexar
              </button>
            )}
            <Link to={`/clientes/${card.cliente_id}`} className="btn-ghost text-xs px-3 py-1.5">
              <ExternalLink className="h-3.5 w-3.5" /> Cliente
            </Link>
          </div>
        </div>
      )}
    </article>
  )
}
