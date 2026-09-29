import { AlertCircle, CheckCircle2, FileText, LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { humanStatus } from '../lib/format'

export function StatusBadge({ status }: { status?: string | null }) {
  const normalized = (status || 'draft').toLowerCase()
  const tone = /approved|accepted|completed|active|answered/.test(normalized) ? 'green' :
    /pending|review|awaiting|needs/.test(normalized) ? 'amber' :
      /rejected|declined|expired|failed/.test(normalized) ? 'coral' : ''
  return <span className={`badge ${tone}`}>{humanStatus(status)}</span>
}

export function Notice({ children, tone = 'info', onRetry }: { children: ReactNode; tone?: 'info' | 'error' | 'success'; onRetry?: () => void }) {
  const Icon = tone === 'error' ? AlertCircle : tone === 'success' ? CheckCircle2 : FileText
  return <div className={`alert ${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
    <Icon size={15} className="shrink-0 mt-[1px]" aria-hidden="true" />
    <div className="flex-1">{children}</div>
    {onRetry && <button className="underline font-semibold" type="button" onClick={onRetry}>Retry</button>}
  </div>
}

export function EmptyState({ icon, title, description, action }: { icon?: ReactNode; title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state">
    <div className="empty-state-icon">{icon || <FileText size={22} strokeWidth={1.5} />}</div>
    <h3>{title}</h3><p>{description}</p>{action}
  </div>
}

export function LoadingPanel({ label = 'Loading workspace…' }: { label?: string }) {
  return <div className="panel p-5" role="status" aria-live="polite">
    <div className="flex items-center gap-2 text-xs text-[#777d75] mb-5"><LoaderCircle size={15} className="animate-spin" />{label}</div>
    <div className="skeleton h-5 w-1/3 mb-4" /><div className="skeleton h-3 w-full mb-2" /><div className="skeleton h-3 w-5/6 mb-2" /><div className="skeleton h-3 w-2/3" />
  </div>
}
