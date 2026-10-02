import { useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, CheckCircle2, Clock, AlertCircle, FileText, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { toast } from 'sonner'
import { api, erroMsg, API_URL } from '../api/client'
import { Carregando, StatusDocBadge } from '../components/ui'
import { dataHora, dataCurta, tamanho } from '../lib/format'

/** Portal do cliente. Sem login: o link é a identificação. */
export default function Portal() {
  const { slug } = useParams()
  const { data, isLoading, error } = useQuery({
    queryKey: ['portal', slug],
    queryFn: () => api.get(`/portal/${slug}`).then((r) => r.data),
    retry: false,
  })

  if (isLoading) return <div className="min-h-screen grid place-items-center"><Carregando /></div>
  if (error) {
    return (
      <div className="min-h-screen grid place-items-center px-4">
        <div className="card p-6 max-w-sm text-center">
          <AlertCircle className="h-8 w-8 text-danger mx-auto mb-2" />
          <p className="font-bold">Link inválido</p>
          <p className="text-sm text-muted mt-1">{erroMsg(error)}</p>
        </div>
      </div>
    )
  }

  const pendentes = data.competencias.filter((c) => !c.completa)
  const completas = data.competencias.filter((c) => c.completa)

  return (
    <div className="min-h-screen">
      <header className="bg-accent text-white px-4 py-6">
        <div className="max-w-2xl mx-auto">
          <p className="text-xs uppercase tracking-wide opacity-80">Portal de documentos</p>
          <h1 className="text-xl font-bold mt-1">{data.cliente_nome}</h1>
          <p className="text-sm opacity-90 mt-1">
            {pendentes.length === 0
              ? 'Tudo em dia. Obrigado!'
              : `Olá${data.responsavel ? `, ${data.responsavel}` : ''}. Envie os documentos abaixo para fecharmos sua contabilidade.`}
          </p>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-5 space-y-4 pb-16">
        {pendentes.length === 0 && (
          <div className="card p-6 text-center">
            <CheckCircle2 className="h-10 w-10 text-success mx-auto mb-2" />
            <p className="font-bold">Nenhuma pendência</p>
            <p className="text-sm text-muted">Quando houver algo a enviar, aparece aqui.</p>
          </div>
        )}
        {pendentes.map((c) => <Competencia key={c.competencia} comp={c} slug={slug} aberta />)}

        {completas.length > 0 && (
          <div className="pt-2">
            <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">Meses concluídos</p>
            <div className="space-y-2">{completas.map((c) => <Competencia key={c.competencia} comp={c} slug={slug} />)}</div>
          </div>
        )}

        {data.historico.length > 0 && (
          <details className="card p-4">
            <summary className="font-semibold text-sm cursor-pointer">Tudo que você já enviou ({data.historico.length})</summary>
            <ul className="mt-3 divide-y divide-border">
              {data.historico.map((d) => (
                <li key={d.id} className="py-2 flex items-center justify-between gap-2 text-xs">
                  <div className="min-w-0">
                    <a className="text-primary hover:underline truncate block" href={`${API_URL}/portal/${slug}/documentos/${d.id}/download`} target="_blank" rel="noopener noreferrer">{d.nome_arquivo}</a>
                    <p className="text-muted">{dataHora(d.created_at)} · {tamanho(d.tamanho)}</p>
                  </div>
                  <StatusDocBadge status={d.status} />
                </li>
              ))}
            </ul>
          </details>
        )}

        <p className="text-[11px] text-muted text-center pt-4">Cada envio fica registrado com data e hora. Dúvidas, fale com a contabilidade.</p>
      </main>
    </div>
  )
}

function Competencia({ comp, slug, aberta = false }) {
  const [open, setOpen] = useState(aberta)
  const faltando = comp.obrigacoes.filter((o) => o.situacao !== 'aceita' && o.situacao !== 'em_analise').length
  return (
    <section className="card overflow-hidden">
      <button className="w-full flex items-center justify-between px-4 py-3 text-left" onClick={() => setOpen((v) => !v)}>
        <div>
          <p className="font-bold">{comp.rotulo}</p>
          <p className="text-xs text-muted">
            {comp.completa ? 'Tudo aceito' : faltando > 0 ? `${faltando} pendente(s) · prazo ${dataCurta(comp.vencimento)}` : 'Aguardando conferência da contabilidade'}
          </p>
        </div>
        {comp.completa ? <CheckCircle2 className="h-5 w-5 text-success" /> : open ? <ChevronUp className="h-4 w-4 text-muted" /> : <ChevronDown className="h-4 w-4 text-muted" />}
      </button>
      {open && (
        <ul className="divide-y divide-border border-t border-border">
          {comp.obrigacoes.map((o) => <Obrigacao key={o.id} o={o} slug={slug} />)}
        </ul>
      )}
    </section>
  )
}

function Obrigacao({ o, slug }) {
  const qc = useQueryClient()
  const ref = useRef(null)
  const [progresso, setProgresso] = useState(0)

  const enviar = useMutation({
    mutationFn: (arquivo) => {
      const fd = new FormData()
      fd.append('obrigacao_id', o.id)
      fd.append('arquivo', arquivo)
      return api.post(`/portal/${slug}/upload`, fd, { onUploadProgress: (e) => setProgresso(Math.round((e.loaded / (e.total || 1)) * 100)) })
    },
    onSuccess: () => {
      toast.success('Recebido! A contabilidade vai conferir.')
      qc.invalidateQueries({ queryKey: ['portal', slug] })
      setProgresso(0)
    },
    onError: (e) => { toast.error(erroMsg(e)); setProgresso(0) },
  })

  const icone = {
    aceita: <CheckCircle2 className="h-5 w-5 text-success" />,
    em_analise: <Clock className="h-5 w-5 text-accent" />,
    corrigir: <AlertCircle className="h-5 w-5 text-warning" />,
    atrasada: <AlertCircle className="h-5 w-5 text-danger" />,
    aguardando: <FileText className="h-5 w-5 text-muted" />,
  }[o.situacao]

  const texto = {
    aceita: 'Aceito pela contabilidade',
    em_analise: 'Enviado. Em conferência.',
    corrigir: `Precisa reenviar: ${o.ultima_rejeicao}`,
    atrasada: 'Em atraso. Envie assim que puder.',
    aguardando: `Envie até ${dataCurta(o.vencimento)}`,
  }[o.situacao]

  const podeEnviar = o.situacao !== 'aceita'
  const ultimo = o.documentos[0]

  return (
    <li className="px-4 py-3 flex items-center gap-3">
      <div className="shrink-0">{icone}</div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-sm">{o.descricao}</p>
        <p className={clsx('text-xs', o.situacao === 'corrigir' ? 'text-warning' : o.situacao === 'atrasada' ? 'text-danger' : 'text-muted')}>{texto}</p>
        {ultimo && o.situacao !== 'aceita' && <p className="text-[11px] text-muted truncate">Último envio: {ultimo.nome_arquivo} · {dataHora(ultimo.created_at)}</p>}
        {enviar.isPending && (
          <div className="h-1.5 bg-raised rounded-full mt-1.5 overflow-hidden"><div className="h-full bg-accent transition-all" style={{ width: `${progresso}%` }} /></div>
        )}
      </div>
      {podeEnviar && (
        <>
          <input ref={ref} type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png,.ofx,.xls,.xlsx,.csv" onChange={(e) => { const f = e.target.files?.[0]; if (f) enviar.mutate(f); e.target.value = '' }} />
          <button className={clsx('btn text-xs px-3 py-2 shrink-0', o.situacao === 'em_analise' ? 'btn-secondary' : 'btn-primary')} onClick={() => ref.current?.click()} disabled={enviar.isPending}>
            {enviar.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {o.situacao === 'em_analise' ? 'Reenviar' : 'Enviar'}
          </button>
        </>
      )}
    </li>
  )
}
