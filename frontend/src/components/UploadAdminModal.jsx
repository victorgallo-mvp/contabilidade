import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload } from 'lucide-react'
import { toast } from 'sonner'
import { api, erroMsg } from '../api/client'
import { Modal, Campo } from './ui'
import { competenciaRotulo } from '../lib/format'

/** Escritório anexa um documento em nome do cliente (chegou por WhatsApp, email...). */
export default function UploadAdminModal({ clienteId, clienteNome, obrigacoes, obrigacaoInicial, onFechar }) {
  const qc = useQueryClient()
  const abertas = (obrigacoes || []).filter((o) => o.situacao !== 'aceita')
  const [obrigacaoId, setObrigacaoId] = useState(obrigacaoInicial || abertas[0]?.id || '')
  const [canal, setCanal] = useState('whatsapp')
  const [arquivo, setArquivo] = useState(null)

  const enviar = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('obrigacao_id', obrigacaoId)
      fd.append('canal', canal)
      fd.append('arquivo', arquivo)
      return api.post(`/admin/clientes/${clienteId}/upload`, fd)
    },
    onSuccess: () => {
      toast.success('Documento anexado e registrado.')
      ;['kanban', 'revisao', 'cliente', 'clientes', 'historico', 'dashboard'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
      onFechar()
    },
    onError: (e) => toast.error(erroMsg(e)),
  })

  return (
    <Modal aberto onFechar={onFechar} titulo={`Anexar em nome de ${clienteNome}`}>
      <div className="space-y-4">
        <Campo label="Pendência">
          <select className="input" value={obrigacaoId} onChange={(e) => setObrigacaoId(e.target.value)}>
            {abertas.length === 0 && <option value="">Nenhuma pendência aberta</option>}
            {abertas.map((o) => (
              <option key={o.id} value={o.id}>{competenciaRotulo(o.competencia)} · {o.descricao}</option>
            ))}
          </select>
        </Campo>
        <Campo label="Como o documento chegou" dica="Fica registrado no histórico como recebido por este canal.">
          <select className="input" value={canal} onChange={(e) => setCanal(e.target.value)}>
            <option value="whatsapp">WhatsApp</option>
            <option value="email">E-mail</option>
            <option value="outro">Outro</option>
          </select>
        </Campo>
        <Campo label="Arquivo">
          <input type="file" className="input" accept=".pdf,.jpg,.jpeg,.png,.ofx,.xls,.xlsx,.csv" onChange={(e) => setArquivo(e.target.files?.[0] || null)} />
        </Campo>
        <div className="flex justify-end gap-2">
          <button className="btn-secondary" onClick={onFechar}>Cancelar</button>
          <button className="btn-primary" onClick={() => enviar.mutate()} disabled={!arquivo || !obrigacaoId || enviar.isPending}>
            <Upload className="h-4 w-4" /> {enviar.isPending ? 'Enviando…' : 'Anexar'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
