import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { MessageCircle } from 'lucide-react'
import { toast } from 'sonner'
import { api, erroMsg } from '../api/client'
import { Modal, Carregando } from './ui'
import { competenciaRotulo } from '../lib/format'

/** Monta a mensagem de cobrança, deixa o admin editar e abre o WhatsApp. Cada clique fica registrado. */
export default function CobrancaModal({ card, onFechar }) {
  const qc = useQueryClient()
  const [msg, setMsg] = useState('')
  const [carregando, setCarregando] = useState(true)

  const clienteId = card?.cliente_id
  const competencia = card?.competencia
  useEffect(() => {
    if (!clienteId || !competencia) return
    let ativo = true
    setCarregando(true)
    api.post('/admin/cobrancas/preview', { cliente_id: clienteId, competencia })
      .then((r) => { if (ativo) setMsg(r.data.mensagem) })
      .catch((e) => { if (ativo) { toast.error(erroMsg(e)); onFechar() } })
      .finally(() => { if (ativo) setCarregando(false) })
    return () => { ativo = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId, competencia])

  const enviar = useMutation({
    mutationFn: () => api.post('/admin/cobrancas', { cliente_id: card.cliente_id, competencia: card.competencia, mensagem: msg }),
    onSuccess: ({ data }) => {
      window.open(data.link, '_blank', 'noopener')
      toast.success('Cobrança registrada. O WhatsApp foi aberto com a mensagem pronta.')
      qc.invalidateQueries({ queryKey: ['kanban'] })
      qc.invalidateQueries({ queryKey: ['historico'] })
      onFechar()
    },
    onError: (e) => toast.error(erroMsg(e)),
  })

  if (!card) return null
  return (
    <Modal aberto={!!card} onFechar={onFechar} titulo={`Cobrar ${card.cliente_nome}`}>
      {carregando ? <Carregando /> : (
        <div className="space-y-3">
          <p className="text-sm text-muted">
            Competência <b className="text-primary">{competenciaRotulo(card.competencia)}</b>
            {card.whatsapp ? <> · WhatsApp <b className="text-primary">{card.whatsapp}</b></> : <> · <span className="text-danger">sem WhatsApp cadastrado</span></>}
          </p>
          <textarea className="input min-h-[220px] font-normal" value={msg} onChange={(e) => setMsg(e.target.value)} />
          <p className="text-xs text-muted">Você pode ajustar o texto. Ao clicar, a cobrança fica registrada no histórico com data e hora, e o WhatsApp abre para você enviar.</p>
          <div className="flex justify-end gap-2 pt-1">
            <button className="btn-secondary" onClick={onFechar}>Cancelar</button>
            <button className="btn-whats" onClick={() => enviar.mutate()} disabled={enviar.isPending || !msg.trim()}>
              <MessageCircle className="h-4 w-4" /> Abrir WhatsApp e registrar
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
