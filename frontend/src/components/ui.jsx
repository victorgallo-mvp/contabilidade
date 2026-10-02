import { useEffect } from 'react'
import clsx from 'clsx'
import { X, Loader2, Inbox } from 'lucide-react'
import { SITUACAO, STATUS_DOC } from '../lib/format'

export function Badge({ children, className }) {
  return (
    <span className={clsx('inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap', className)}>
      {children}
    </span>
  )
}

export function SituacaoBadge({ situacao }) {
  const s = SITUACAO[situacao] || { rotulo: situacao, cls: 'bg-raised text-muted' }
  return <Badge className={s.cls}>{s.rotulo}</Badge>
}

export function StatusDocBadge({ status }) {
  const s = STATUS_DOC[status] || { rotulo: status, cls: 'bg-raised text-muted' }
  return <Badge className={s.cls}>{s.rotulo}</Badge>
}

export function Spinner({ className }) {
  return <Loader2 className={clsx('animate-spin text-muted', className || 'h-5 w-5')} />
}

export function Carregando({ texto = 'Carregando…' }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted py-10 justify-center">
      <Spinner /> {texto}
    </div>
  )
}

export function Vazio({ titulo, texto, icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center text-center py-12 px-4 text-muted">
      <Icon className="h-8 w-8 mb-3 opacity-60" />
      <p className="font-semibold text-primary">{titulo}</p>
      {texto && <p className="text-sm mt-1 max-w-sm">{texto}</p>}
    </div>
  )
}

export function Modal({ aberto, onFechar, titulo, children, largura = 'max-w-lg' }) {
  useEffect(() => {
    if (!aberto) return
    const h = (e) => e.key === 'Escape' && onFechar()
    window.addEventListener('keydown', h)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', h)
      document.body.style.overflow = ''
    }
  }, [aberto, onFechar])
  if (!aberto) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" onMouseDown={onFechar}>
      <div className="absolute inset-0 bg-black/40" />
      <div
        className={clsx('relative w-full bg-surface rounded-t-2xl sm:rounded-2xl shadow-xl animate-fade-in max-h-[92vh] flex flex-col', largura)}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="font-bold text-base">{titulo}</h3>
          <button onClick={onFechar} className="btn-ghost p-1.5 rounded-lg" aria-label="Fechar">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-5 py-4 overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}

export function Campo({ label, children, dica }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
      {dica && <p className="text-xs text-muted mt-1">{dica}</p>}
    </div>
  )
}

export function Stat({ rotulo, valor, tom = 'text-primary', onClick }) {
  return (
    <button
      onClick={onClick}
      className={clsx('card px-4 py-3 text-left flex-1 min-w-[130px]', onClick && 'hover:bg-raised transition')}
    >
      <p className="text-xs text-muted font-medium">{rotulo}</p>
      <p className={clsx('text-2xl font-bold mt-0.5', tom)}>{valor}</p>
    </button>
  )
}
