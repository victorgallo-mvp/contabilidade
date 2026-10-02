import { format, formatDistanceToNowStrict, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export const dataHora = (iso) => (iso ? format(parseISO(iso), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR }) : '')
export const dataCurta = (iso) => (iso ? format(parseISO(iso), 'dd/MM/yyyy', { locale: ptBR }) : '')
export const relativo = (iso) => (iso ? formatDistanceToNowStrict(parseISO(iso), { locale: ptBR, addSuffix: true }) : '')

export const tamanho = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export const TIPOS_DOC = {
  extrato: 'Extrato bancário',
  nf_entrada: 'Notas fiscais de entrada',
  recibo: 'Recibos e comprovantes',
}

export const TIPOS_EVENTO = {
  acesso_portal: 'Acesso ao portal',
  upload: 'Documento enviado',
  upload_admin: 'Anexado pelo escritório',
  download: 'Documento aberto',
  aceite: 'Documento aceito',
  rejeicao: 'Documento rejeitado',
  cobranca: 'Cobrança enviada',
  cliente_criado: 'Cliente cadastrado',
  cliente_alterado: 'Cadastro alterado',
  ia_leitura: 'Leitura automática',
}

export const SITUACAO = {
  aguardando: { rotulo: 'Aguardando', cls: 'bg-info-soft text-info' },
  atrasada: { rotulo: 'Atrasado', cls: 'bg-danger-soft text-danger' },
  corrigir: { rotulo: 'Corrigir', cls: 'bg-warning-soft text-warning' },
  em_analise: { rotulo: 'Em análise', cls: 'bg-accent-soft text-accent' },
  aceita: { rotulo: 'Aceito', cls: 'bg-success-soft text-success' },
}

export const STATUS_DOC = {
  em_analise: { rotulo: 'Em análise', cls: 'bg-accent-soft text-accent' },
  aceito: { rotulo: 'Aceito', cls: 'bg-success-soft text-success' },
  rejeitado: { rotulo: 'Rejeitado', cls: 'bg-danger-soft text-danger' },
}

export const competenciaRotulo = (comp) => {
  if (!comp) return ''
  const meses = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
  const [a, m] = comp.split('-')
  return `${meses[parseInt(m, 10) - 1]}/${a}`
}

export const mesAtual = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}
