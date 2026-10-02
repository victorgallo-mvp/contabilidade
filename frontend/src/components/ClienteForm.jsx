import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { api, erroMsg } from '../api/client'
import { Modal, Campo } from './ui'
import { TIPOS_DOC, mesAtual } from '../lib/format'

const mesAnterior = () => {
  const d = new Date()
  d.setMonth(d.getMonth() - 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export default function ClienteForm({ cliente, onFechar }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const editando = !!cliente
  const [f, setF] = useState(() => cliente ? {
    nome: cliente.nome, cnpj: cliente.cnpj || '', responsavel: cliente.responsavel || '', whatsapp: cliente.whatsapp || '',
    email: cliente.email || '', mes_inicio: cliente.mes_inicio, dia_corte: cliente.dia_corte, tipos_ativos: cliente.tipos_ativos,
    observacoes: cliente.observacoes || '', ativo: cliente.ativo,
  } : {
    nome: '', cnpj: '', responsavel: '', whatsapp: '', email: '', mes_inicio: mesAnterior(), dia_corte: 10,
    tipos_ativos: ['extrato'], observacoes: '', ativo: true,
  })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const toggleTipo = (t) => setF({ ...f, tipos_ativos: f.tipos_ativos.includes(t) ? f.tipos_ativos.filter((x) => x !== t) : [...f.tipos_ativos, t] })

  const salvar = useMutation({
    mutationFn: () => {
      const body = { ...f, dia_corte: Number(f.dia_corte), cnpj: f.cnpj || null, responsavel: f.responsavel || null,
        whatsapp: f.whatsapp || null, email: f.email || null, observacoes: f.observacoes || null }
      return editando ? api.put(`/admin/clientes/${cliente.id}`, body) : api.post('/admin/clientes', body)
    },
    onSuccess: ({ data }) => {
      toast.success(editando ? 'Cadastro atualizado.' : 'Cliente criado. Agora cadastre as contas bancárias.')
      ;['clientes', 'cliente', 'kanban', 'dashboard'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
      onFechar()
      if (!editando) navigate(`/clientes/${data.id}`)
    },
    onError: (e) => toast.error(erroMsg(e)),
  })

  return (
    <Modal aberto onFechar={onFechar} titulo={editando ? 'Editar cliente' : 'Novo cliente'} largura="max-w-xl">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="sm:col-span-2"><Campo label="Nome da empresa / cliente"><input className="input" value={f.nome} onChange={set('nome')} autoFocus /></Campo></div>
        <Campo label="CNPJ"><input className="input" value={f.cnpj} onChange={set('cnpj')} /></Campo>
        <Campo label="Responsável (primeiro nome p/ mensagens)"><input className="input" value={f.responsavel} onChange={set('responsavel')} /></Campo>
        <Campo label="WhatsApp" dica="Com DDD. Ex.: 31999990000"><input className="input" value={f.whatsapp} onChange={set('whatsapp')} inputMode="tel" /></Campo>
        <Campo label="E-mail"><input className="input" value={f.email} onChange={set('email')} type="email" /></Campo>
        <Campo label="Cobrar a partir de (competência)" dica="Primeiro mês que o sistema vai exigir documentos.">
          <input className="input" type="month" value={f.mes_inicio} onChange={set('mes_inicio')} max={mesAtual()} />
        </Campo>
        <Campo label="Dia de corte" dica="Dia do mês seguinte em que a competência passa a atrasada.">
          <input className="input" type="number" min={1} max={28} value={f.dia_corte} onChange={set('dia_corte')} />
        </Campo>
        <div className="sm:col-span-2">
          <Campo label="Documentos esperados todo mês" dica="Extrato gera uma pendência por conta bancária cadastrada.">
            <div className="flex flex-wrap gap-2">
              {Object.entries(TIPOS_DOC).map(([k, v]) => (
                <label key={k} className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm cursor-pointer ${f.tipos_ativos.includes(k) ? 'border-accent bg-accent-soft text-accent' : 'border-border'}`}>
                  <input type="checkbox" className="accent-accent" checked={f.tipos_ativos.includes(k)} onChange={() => toggleTipo(k)} /> {v}
                </label>
              ))}
            </div>
          </Campo>
        </div>
        <div className="sm:col-span-2"><Campo label="Observações internas"><textarea className="input" rows={2} value={f.observacoes} onChange={set('observacoes')} /></Campo></div>
        {editando && (
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="accent-accent" checked={f.ativo} onChange={(e) => setF({ ...f, ativo: e.target.checked })} /> Cliente ativo</label>
        )}
      </div>
      <div className="flex justify-end gap-2 mt-4">
        <button className="btn-secondary" onClick={onFechar}>Cancelar</button>
        <button className="btn-primary" onClick={() => salvar.mutate()} disabled={!f.nome.trim() || !f.mes_inicio || salvar.isPending}>
          {salvar.isPending ? 'Salvando…' : 'Salvar'}
        </button>
      </div>
    </Modal>
  )
}
