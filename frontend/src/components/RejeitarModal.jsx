import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageCircle, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { api, erroMsg } from '../api/client'
import { Modal } from './ui'

const MOTIVOS = [
  'Extrato incompleto: precisamos do mês inteiro.',
  'Documento de outro mês.',
  'Arquivo ilegível ou cortado.',
  'Extrato de outra conta bancária.',
]

export default function RejeitarModal({ item, onFechar }) {
  const qc = useQueryClient()
  const [motivo, setMotivo] = useState('')
  const [resultado, setResultado] = useState(null)

  const rejeitar = useMutation({
    mutationFn: () => api.post(`/admin/documentos/${item.documento.id}/rejeitar`, { motivo }),
    onSuccess: ({ data }) => {
      setResultado(data)
      ;['kanban', 'revisao', 'cliente', 'clientes', 'historico', 'dashboard'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
    },
    onError: (e) => toast.error(erroMsg(e)),
  })

  if (!item) return null
  return (
    <Modal aberto onFechar={onFechar} titulo="Rejeitar documento">
      {!resultado ? (
        <div className="space-y-3">
          <p className="text-sm text-muted">
            <b className="text-primary">{item.cliente_nome}</b> · {item.obrigacao.descricao} · {item.obrigacao.competencia_rotulo}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {MOTIVOS.map((m) => (
              <button key={m} onClick={() => setMotivo(m)} className="text-xs rounded-full border border-border px-2.5 py-1 hover:bg-raised">{m}</button>
            ))}
          </div>
          <textarea className="input min-h-[100px]" placeholder="Explique o que precisa ser corrigido. O cliente vê este texto no portal." value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={onFechar}>Cancelar</button>
            <button className="btn-danger" onClick={() => rejeitar.mutate()} disabled={motivo.trim().length < 3 || rejeitar.isPending}>
              <XCircle className="h-4 w-4" /> Rejeitar
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm">Documento rejeitado e registrado. O cliente já vê o motivo no portal. Quer avisar pelo WhatsApp?</p>
          <pre className="text-xs whitespace-pre-wrap bg-raised rounded-xl p-3 border border-border font-sans">{resultado.mensagem}</pre>
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={onFechar}>Fechar</button>
            <a className="btn-whats" href={resultado.whatsapp_link} target="_blank" rel="noopener noreferrer" onClick={onFechar}>
              <MessageCircle className="h-4 w-4" /> Avisar no WhatsApp
            </a>
          </div>
        </div>
      )}
    </Modal>
  )
}
