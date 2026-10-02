import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Copy, ExternalLink, Pencil, Plus, Trash2, Paperclip, MessageCircle, Eye, History } from 'lucide-react'
import { toast } from 'sonner'
import { api, erroMsg, abrirArquivo } from '../api/client'
import { Carregando, SituacaoBadge, StatusDocBadge, Badge, Campo } from '../components/ui'
import ClienteForm from '../components/ClienteForm'
import UploadAdminModal from '../components/UploadAdminModal'
import CobrancaModal from '../components/CobrancaModal'
import { dataHora, dataCurta, tamanho, competenciaRotulo } from '../lib/format'

export default function ClienteDetalhe() {
  const { id } = useParams()
  const qc = useQueryClient()
  const [editar, setEditar] = useState(false)
  const [anexar, setAnexar] = useState(null)
  const [cobrar, setCobrar] = useState(null)
  const [novaConta, setNovaConta] = useState({ banco: '', apelido: '' })

  const { data: c, isLoading } = useQuery({ queryKey: ['cliente', id], queryFn: () => api.get(`/admin/clientes/${id}`).then((r) => r.data) })
  const { data: obs } = useQuery({ queryKey: ['cliente', id, 'obrigacoes'], queryFn: () => api.get(`/admin/clientes/${id}/obrigacoes`).then((r) => r.data), refetchInterval: 30_000 })

  const invalidar = () => ['cliente', 'clientes', 'kanban', 'dashboard', 'historico'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))

  const addConta = useMutation({
    mutationFn: () => api.post(`/admin/clientes/${id}/contas`, { banco: novaConta.banco, apelido: novaConta.apelido || null }),
    onSuccess: () => { setNovaConta({ banco: '', apelido: '' }); toast.success('Conta adicionada.'); invalidar() },
    onError: (e) => toast.error(erroMsg(e)),
  })
  const delConta = useMutation({
    mutationFn: (contaId) => api.delete(`/admin/clientes/${id}/contas/${contaId}`),
    onSuccess: () => { toast.success('Conta removida ou desativada.'); invalidar() },
    onError: (e) => toast.error(erroMsg(e)),
  })

  if (isLoading || !c) return <Carregando />

  const porComp = {}
  for (const o of obs || []) (porComp[o.competencia] ||= []).push(o)
  const competencias = Object.keys(porComp).sort().reverse()

  const copiar = () => navigator.clipboard.writeText(c.link_portal).then(() => toast.success('Link copiado.'))

  return (
    <div className="space-y-5">
      <Link to="/clientes" className="btn-ghost text-xs px-2 py-1 -ml-2"><ArrowLeft className="h-3.5 w-3.5" /> Clientes</Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">{c.nome}</h1>
          <p className="text-sm text-muted">{c.cnpj || 'sem CNPJ'} · {c.responsavel || '—'} · {c.whatsapp || 'sem WhatsApp'} · {c.email || 'sem e-mail'}</p>
          {!c.ativo && <Badge className="bg-danger-soft text-danger mt-1">inativo</Badge>}
        </div>
        <div className="flex gap-2">
          <Link to={`/historico?cliente_id=${c.id}`} className="btn-secondary"><History className="h-4 w-4" /> Histórico</Link>
          <button className="btn-secondary" onClick={() => setEditar(true)}><Pencil className="h-4 w-4" /> Editar</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="card p-4 space-y-3">
          <h2 className="font-bold text-sm">Link do portal</h2>
          <p className="text-xs text-muted">Link fixo deste cliente. Não expira. Envie uma vez e ele usa sempre.</p>
          <div className="flex items-center gap-2">
            <input className="input text-xs" readOnly value={c.link_portal} onFocus={(e) => e.target.select()} />
            <button className="btn-secondary px-2.5" onClick={copiar} title="Copiar"><Copy className="h-4 w-4" /></button>
            <a className="btn-secondary px-2.5" href={c.link_portal} target="_blank" rel="noopener noreferrer" title="Abrir"><ExternalLink className="h-4 w-4" /></a>
          </div>
          <a className="btn-whats w-full text-xs" target="_blank" rel="noopener noreferrer"
            href={`https://wa.me/${(c.whatsapp || '').replace(/\D/g, '').replace(/^(?!55)/, '55')}?text=${encodeURIComponent(`Olá ${c.responsavel || ''}! Este é o seu portal para enviar extratos e documentos para a contabilidade. Guarde este link:\n${c.link_portal}`)}`}>
            <MessageCircle className="h-3.5 w-3.5" /> Enviar link por WhatsApp
          </a>
        </section>

        <section className="card p-4 space-y-3">
          <h2 className="font-bold text-sm">Configuração mensal</h2>
          <p className="text-xs text-muted">Cobra desde <b className="text-primary">{competenciaRotulo(c.mes_inicio)}</b> · corte dia <b className="text-primary">{c.dia_corte}</b> do mês seguinte</p>
          <div className="flex flex-wrap gap-1.5">
            {c.tipos_ativos.map((t) => <Badge key={t} className="bg-accent-soft text-accent">{{ extrato: 'Extrato', nf_entrada: 'NF de entrada', recibo: 'Recibos' }[t] || t}</Badge>)}
          </div>
        </section>

        <section className="card p-4 space-y-3">
          <h2 className="font-bold text-sm">Contas bancárias</h2>
          <ul className="space-y-1">
            {c.contas.length === 0 && <li className="text-xs text-muted">Nenhuma conta. Sem conta, não há pendência de extrato.</li>}
            {c.contas.map((k) => (
              <li key={k.id} className="flex items-center justify-between text-sm">
                <span className={!k.ativa ? 'line-through text-muted' : ''}>{k.rotulo}</span>
                {k.ativa && <button className="btn-ghost p-1" onClick={() => delConta.mutate(k.id)} title="Remover"><Trash2 className="h-3.5 w-3.5" /></button>}
              </li>
            ))}
          </ul>
          <div className="flex gap-1.5">
            <input className="input text-xs" placeholder="Banco" value={novaConta.banco} onChange={(e) => setNovaConta({ ...novaConta, banco: e.target.value })} />
            <input className="input text-xs" placeholder="Apelido" value={novaConta.apelido} onChange={(e) => setNovaConta({ ...novaConta, apelido: e.target.value })} />
            <button className="btn-primary px-2.5" onClick={() => addConta.mutate()} disabled={!novaConta.banco.trim() || addConta.isPending}><Plus className="h-4 w-4" /></button>
          </div>
        </section>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">Pendências por mês</h2>
          <button className="btn-secondary text-xs" onClick={() => setAnexar({})}><Paperclip className="h-3.5 w-3.5" /> Anexar em nome do cliente</button>
        </div>
        {competencias.length === 0 && <p className="text-sm text-muted">Nenhuma pendência gerada ainda.</p>}
        {competencias.map((comp) => {
          const lista = porComp[comp]
          const temPend = lista.some((o) => ['atrasada', 'aguardando', 'corrigir'].includes(o.situacao))
          return (
            <div key={comp} className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-sm">{competenciaRotulo(comp)} <span className="text-muted font-normal text-xs">· vence {dataCurta(lista[0].vencimento)}</span></h3>
                {temPend && (
                  <button className="btn-whats text-xs px-3 py-1.5" onClick={() => setCobrar({ cliente_id: c.id, cliente_nome: c.nome, whatsapp: c.whatsapp, competencia: comp })}>
                    <MessageCircle className="h-3.5 w-3.5" /> Cobrar
                  </button>
                )}
              </div>
              <ul className="divide-y divide-border">
                {lista.map((o) => (
                  <li key={o.id} className="py-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm">{o.descricao}</span>
                      <div className="flex items-center gap-2">
                        {o.situacao !== 'aceita' && <button className="btn-ghost text-xs px-2 py-1" onClick={() => setAnexar({ obrigacaoId: o.id })}><Paperclip className="h-3.5 w-3.5" /></button>}
                        <SituacaoBadge situacao={o.situacao} />
                      </div>
                    </div>
                    {o.ultima_rejeicao && o.situacao === 'corrigir' && <p className="text-xs text-warning mt-0.5">Motivo: {o.ultima_rejeicao}</p>}
                    {o.documentos.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {o.documentos.map((d) => (
                          <li key={d.id} className="flex items-center gap-2 text-xs text-muted">
                            <button className="hover:underline inline-flex items-center gap-1 text-primary" onClick={() => abrirArquivo(`/admin/documentos/${d.id}/download`)}>
                              <Eye className="h-3 w-3" /> {d.nome_arquivo}
                            </button>
                            <span>{tamanho(d.tamanho)} · {dataHora(d.created_at)} · {d.enviado_por === 'admin' ? `anexado por ${d.enviado_por_nome} (${d.canal})` : 'pelo cliente'}</span>
                            <StatusDocBadge status={d.status} />
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </section>

      {editar && <ClienteForm cliente={c} onFechar={() => setEditar(false)} />}
      {anexar && <UploadAdminModal clienteId={c.id} clienteNome={c.nome} obrigacoes={obs || []} obrigacaoInicial={anexar.obrigacaoId} onFechar={() => setAnexar(null)} />}
      <CobrancaModal card={cobrar} onFechar={() => setCobrar(null)} />
    </div>
  )
}
