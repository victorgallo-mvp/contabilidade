import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Eye, CheckCircle2, XCircle, AlertTriangle, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { api, erroMsg, abrirArquivo } from '../api/client'
import { Carregando, Vazio, Badge } from '../components/ui'
import RejeitarModal from '../components/RejeitarModal'
import { dataHora, tamanho } from '../lib/format'

export default function Revisao() {
  const qc = useQueryClient()
  const [rejeitar, setRejeitar] = useState(null)
  const { data, isLoading } = useQuery({
    queryKey: ['revisao'],
    queryFn: () => api.get('/admin/documentos/revisao').then((r) => r.data),
    refetchInterval: 30_000,
  })

  const aceitar = useMutation({
    mutationFn: (id) => api.post(`/admin/documentos/${id}/aceitar`),
    onSuccess: () => {
      toast.success('Documento aceito.')
      ;['kanban', 'revisao', 'cliente', 'clientes', 'historico', 'dashboard'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
    },
    onError: (e) => toast.error(erroMsg(e)),
  })

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold">Fila de revisão</h1>
        <p className="text-sm text-muted">Documentos enviados que ainda não foram conferidos. Só o escritório aceita ou rejeita.</p>
      </div>

      {isLoading ? <Carregando /> : !data?.length ? (
        <Vazio titulo="Nada para revisar" texto="Quando um cliente enviar um documento, ele aparece aqui." icon={CheckCircle2} />
      ) : (
        <ul className="space-y-3">
          {data.map((item) => (
            <li key={item.documento.id} className="card p-4 animate-fade-in">
              <div className="flex flex-col md:flex-row md:items-start gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link to={`/clientes/${item.obrigacao.cliente_id}`} className="font-semibold hover:underline">{item.cliente_nome}</Link>
                    <Badge className="bg-raised text-muted">{item.obrigacao.competencia_rotulo}</Badge>
                    <Badge className="bg-accent-soft text-accent">{item.obrigacao.descricao}</Badge>
                    {item.documento.enviado_por === 'admin' && <Badge className="bg-raised text-muted">anexado por {item.documento.enviado_por_nome} via {item.documento.canal}</Badge>}
                  </div>
                  <p className="text-sm mt-1 break-all">{item.documento.nome_arquivo}</p>
                  <p className="text-xs text-muted">{tamanho(item.documento.tamanho)} · {dataHora(item.documento.created_at)}</p>
                  <LeituraIA d={item.documento} />
                </div>
                <div className="flex flex-wrap gap-2 shrink-0 [&>button]:flex-1 md:[&>button]:flex-none">
                  <button className="btn-secondary" onClick={() => abrirArquivo(`/admin/documentos/${item.documento.id}/download`)}>
                    <Eye className="h-4 w-4" /> Abrir
                  </button>
                  <button className="btn-danger" onClick={() => setRejeitar(item)}>
                    <XCircle className="h-4 w-4" /> Rejeitar
                  </button>
                  <button className="btn-success" onClick={() => aceitar.mutate(item.documento.id)} disabled={aceitar.isPending}>
                    <CheckCircle2 className="h-4 w-4" /> Aceitar
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {rejeitar && <RejeitarModal item={rejeitar} onFechar={() => setRejeitar(null)} />}
    </div>
  )
}

export function LeituraIA({ d }) {
  if (d.ia_status === 'pendente') return <p className="text-xs text-muted mt-2 inline-flex items-center gap-1"><Sparkles className="h-3 w-3" /> Lendo o documento…</p>
  if (d.ia_status === 'pulado' || d.ia_status === 'erro') return null
  return (
    <div className={`mt-2 rounded-xl px-3 py-2 text-xs ${d.ia_status === 'alerta' ? 'bg-warning-soft text-warning' : 'bg-raised text-muted'}`}>
      <p>
        {d.ia_status === 'alerta' ? <AlertTriangle className="h-3 w-3 inline -mt-0.5 mr-1" /> : <Sparkles className="h-3 w-3 inline -mt-0.5 mr-1" />}
        <span className="font-semibold">{d.ia_status === 'alerta' ? 'Conferir: ' : 'Leitura automática: '}</span>
        {d.ia_alerta || d.ia_resumo}
      </p>
      {(d.ia_banco || d.ia_periodo_inicio || d.ia_saldo_final) && (
        <p className="mt-0.5 opacity-90">
          {d.ia_banco && <>Banco: {d.ia_banco} · </>}
          {d.ia_periodo_inicio && <>Período: {d.ia_periodo_inicio} a {d.ia_periodo_fim} · </>}
          {d.ia_saldo_inicial && <>Saldo inicial {d.ia_saldo_inicial} · </>}
          {d.ia_saldo_final && <>Saldo final {d.ia_saldo_final}</>}
        </p>
      )}
    </div>
  )
}
