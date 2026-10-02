import { useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Download, Search, Eye } from 'lucide-react'
import { toast } from 'sonner'
import { api, baixarArquivo, abrirArquivo, erroMsg } from '../api/client'
import { Carregando, Vazio, Badge } from '../components/ui'
import { dataHora, TIPOS_EVENTO, TIPOS_DOC, competenciaRotulo } from '../lib/format'

const COR_EVENTO = {
  upload: 'bg-accent-soft text-accent', upload_admin: 'bg-accent-soft text-accent', aceite: 'bg-success-soft text-success',
  rejeicao: 'bg-danger-soft text-danger', cobranca: 'bg-warning-soft text-warning', acesso_portal: 'bg-raised text-muted',
  download: 'bg-raised text-muted', ia_leitura: 'bg-info-soft text-info',
}

export default function Historico() {
  const [sp, setSp] = useSearchParams()
  const [f, setF] = useState({
    cliente_id: sp.get('cliente_id') || '', tipo_evento: 'todos', tipo_documento: 'todos', competencia: 'todas',
    inicio: '', fim: '', busca: '',
  })
  const [aplicado, setAplicado] = useState(f)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const { data: clientes } = useQuery({ queryKey: ['clientes', 'todos'], queryFn: () => api.get('/admin/clientes', { params: { incluir_inativos: true } }).then((r) => r.data) })
  const { data: kb } = useQuery({ queryKey: ['kanban', 'todas'], queryFn: () => api.get('/admin/kanban', { params: { competencia: 'todas' } }).then((r) => r.data) })
  const params = Object.fromEntries(Object.entries(aplicado).filter(([, v]) => v !== '' && v !== 'todos' && v !== 'todas'))
  const { data, isLoading } = useQuery({ queryKey: ['historico', params], queryFn: () => api.get('/admin/historico', { params: { ...params, limit: 500 } }).then((r) => r.data) })

  const aplicar = () => { setAplicado(f); if (f.cliente_id) setSp({ cliente_id: f.cliente_id }); else setSp({}) }
  const exportar = () => {
    const qs = new URLSearchParams(params).toString()
    baixarArquivo(`/admin/historico.csv?${qs}`, 'historico.csv').catch((e) => toast.error(erroMsg(e)))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">Histórico completo</h1>
          <p className="text-sm text-muted">Todo envio, cobrança, aceite e acesso, com data, hora e origem. Nada aqui é apagado.</p>
        </div>
        <button className="btn-secondary" onClick={exportar}><Download className="h-4 w-4" /> Exportar CSV</button>
      </div>

      <div className="card p-4 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="col-span-2">
          <label className="label">Cliente</label>
          <select className="input" value={f.cliente_id} onChange={set('cliente_id')}>
            <option value="">Todos</option>
            {(clientes || []).map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Evento</label>
          <select className="input" value={f.tipo_evento} onChange={set('tipo_evento')}>
            <option value="todos">Todos</option>
            {Object.entries(TIPOS_EVENTO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Documento</label>
          <select className="input" value={f.tipo_documento} onChange={set('tipo_documento')}>
            <option value="todos">Todos</option>
            {Object.entries(TIPOS_DOC).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Competência</label>
          <select className="input" value={f.competencia} onChange={set('competencia')}>
            <option value="todas">Todas</option>
            {(kb?.competencias || []).map((c) => <option key={c} value={c}>{competenciaRotulo(c)}</option>)}
          </select>
        </div>
        <div><label className="label">De</label><input className="input" type="date" value={f.inicio} onChange={set('inicio')} /></div>
        <div><label className="label">Até</label><input className="input" type="date" value={f.fim} onChange={set('fim')} /></div>
        <div className="col-span-2 md:col-span-3 lg:col-span-6">
          <label className="label">Busca livre</label>
          <input className="input" placeholder="Nome do arquivo, texto da descrição…" value={f.busca} onChange={set('busca')} onKeyDown={(e) => e.key === 'Enter' && aplicar()} />
        </div>
        <div className="flex items-end"><button className="btn-primary w-full" onClick={aplicar}><Search className="h-4 w-4" /> Filtrar</button></div>
      </div>

      {isLoading ? <Carregando /> : !data?.length ? <Vazio titulo="Nenhum registro" texto="Ajuste os filtros." /> : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm min-w-[820px]">
            <thead className="text-xs text-muted uppercase tracking-wide bg-raised">
              <tr>
                <th className="text-left px-4 py-2 font-semibold">Data e hora</th>
                <th className="text-left px-4 py-2 font-semibold">Cliente</th>
                <th className="text-left px-4 py-2 font-semibold">Evento</th>
                <th className="text-left px-4 py-2 font-semibold">Detalhe</th>
                <th className="text-left px-4 py-2 font-semibold">Quem</th>
                <th className="text-left px-4 py-2 font-semibold">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.map((e) => (
                <tr key={e.id} className="hover:bg-raised">
                  <td className="px-4 py-2 whitespace-nowrap text-xs">{dataHora(e.created_at)}</td>
                  <td className="px-4 py-2 max-w-[200px] truncate">{e.cliente_id ? <Link className="hover:underline" to={`/clientes/${e.cliente_id}`}>{e.cliente_nome}</Link> : '—'}</td>
                  <td className="px-4 py-2"><Badge className={COR_EVENTO[e.tipo] || 'bg-raised text-muted'}>{e.tipo_rotulo}</Badge></td>
                  <td className="px-4 py-2 max-w-[360px]">
                    <p className="truncate">{e.descricao}</p>
                    {e.documento_id && (
                      <button className="text-xs text-accent hover:underline inline-flex items-center gap-1" onClick={() => abrirArquivo(`/admin/documentos/${e.documento_id}/download`)}>
                        <Eye className="h-3 w-3" /> {e.documento_nome}
                      </button>
                    )}
                    {e.competencia && <span className="text-xs text-muted ml-2">{competenciaRotulo(e.competencia)}</span>}
                  </td>
                  <td className="px-4 py-2 text-xs">{e.ator}</td>
                  <td className="px-4 py-2 text-xs text-muted">{e.ip || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.length >= 500 && <p className="text-xs text-muted px-4 py-2">Mostrando os 500 mais recentes. Refine os filtros ou exporte o CSV para ver tudo.</p>}
        </div>
      )}
    </div>
  )
}
