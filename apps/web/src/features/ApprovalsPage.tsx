import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, ClipboardCheck, X } from 'lucide-react'
import { api } from '../lib/api'
import { humanStatus, messageOf, money, shortDate } from '../lib/format'
import type { Approval, Role } from '../lib/types'
import { EmptyState, LoadingPanel, Notice, StatusBadge } from '../components/Ui'

export function ApprovalsPage({ role, onOpenBrief }: { role: Role; onOpenBrief: (id: string) => void }) {
  const client = useQueryClient()
  const approvals = useQuery({ queryKey: ['approvals'], queryFn: api.listApprovals })
  const [selected, setSelected] = useState<Approval | null>(null)
  const [note, setNote] = useState('')
  const [result, setResult] = useState('')
  const decision = useMutation({
    mutationFn: ({ id, choice }: { id: string; choice: 'approved' | 'rejected' }) => api.decideApproval(id, choice, note.trim() || undefined),
    onSuccess: (value) => { setResult(`Review ${humanStatus(value.status).toLowerCase()}. The quote version is now updated.`); setSelected(null); setNote(''); client.invalidateQueries({ queryKey: ['approvals'] }); client.invalidateQueries({ queryKey: ['quote'] }) },
  })
  const pending = approvals.data?.filter((item) => item.status === 'pending') || []
  const finished = approvals.data?.filter((item) => item.status !== 'pending') || []

  return <div className="page">
    <div className="page-header"><div><div className="eyebrow">Commercial guardrail</div><h1 className="page-title">Review with intention.</h1><p className="page-subtitle">Each decision is bound to one exact quote version. A changed price or scope needs a fresh review.</p></div><span className="badge amber">{pending.length} AWAITING REVIEW</span></div>
    {result && <div className="mb-5"><Notice tone="success">{result}</Notice></div>}
    {decision.isError && <div className="mb-5"><Notice tone="error">{messageOf(decision.error)}</Notice></div>}
    {approvals.isPending ? <LoadingPanel label="Loading review queue…" /> : approvals.isError ? <Notice tone="error" onRetry={() => approvals.refetch()}>{messageOf(approvals.error)}</Notice> : <>
      <div className="panel mb-5"><div className="panel-header"><div className="panel-heading">Needs a decision</div><span className="eyebrow">{pending.length} OPEN</span></div>
        {pending.length === 0 ? <EmptyState icon={<ClipboardCheck size={22} />} title="A clear desk" description="Quotes requiring an internal decision will appear here." /> :
          <div className="divide-y divide-[#f0ede7]">{pending.map((item) => <div key={item.id} className="p-5 flex flex-wrap items-center gap-4 justify-between">
            <div className="min-w-[180px]"><div className="font-semibold text-[12px] text-[#2e352e]">{item.client_name || `Quote version ${item.quote_version_id.slice(0, 8)}`}</div><div className="text-[10px] text-[#92988f] mt-1">Submitted {shortDate(item.created_at)} · Version {item.quote_version_id.slice(0, 8)}</div></div>
            <div className="flex items-center gap-4"><div className="serif text-[20px]">{item.total ? money(item.total) : '—'}</div><StatusBadge status={item.status} />
              {item.brief_id && <button className="btn btn-small" type="button" onClick={() => onOpenBrief(item.brief_id!)} title="Open related brief">Open <ArrowRight size={12} /></button>}
              <button className="btn btn-small btn-primary" type="button" onClick={() => { setSelected(item); setNote('') }}>Review</button></div>
          </div>)}</div>}
      </div>
      {finished.length > 0 && <div className="panel"><div className="panel-header"><div className="panel-heading">Decision history</div></div><div className="table-wrap"><table className="data-table"><thead><tr><th>Quote version</th><th>Decision</th><th>Date</th><th>Note</th></tr></thead><tbody>{finished.map((item) => <tr key={item.id}><td>{item.quote_version_id.slice(0, 12)}</td><td><StatusBadge status={item.status} /></td><td>{shortDate(item.created_at)}</td><td>{item.note || '—'}</td></tr>)}</tbody></table></div></div>}
    </>}
    {selected && <div className="fixed inset-0 z-50 bg-[#1f2722]/50 p-4 flex items-center justify-center" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelected(null) }}>
      <div className="panel w-full max-w-[500px] shadow-xl" role="dialog" aria-modal="true" aria-labelledby="review-title"><div className="panel-header"><div><div className="eyebrow">Version-bound approval</div><h2 id="review-title" className="serif text-[25px] mt-1">Review this quote</h2></div><button className="icon-btn" type="button" aria-label="Close review" onClick={() => setSelected(null)}><X size={15} /></button></div>
        <div className="panel-body"><p className="text-[12px] leading-[1.65] text-[#626a60] mb-4">This decision applies only to version <strong>{selected.quote_version_id}</strong>. Editing its scope, price, or terms invalidates this approval.</p>
          <div className="field"><label htmlFor="decision-note">DECISION NOTE</label><textarea id="decision-note" className="textarea" rows={4} placeholder="Record the reason or any conditions…" value={note} onChange={(event) => setNote(event.target.value)} /></div>
          {role !== 'admin' && <div className="mt-4"><Notice tone="info">Only an admin may approve commercial exceptions in this workspace.</Notice></div>}
          <div className="flex justify-end flex-wrap gap-2 mt-6"><button className="btn" type="button" onClick={() => setSelected(null)}>Cancel</button><button className="btn btn-danger" type="button" disabled={role !== 'admin' || decision.isPending} onClick={() => decision.mutate({ id: selected.id, choice: 'rejected' })}>Reject</button><button className="btn btn-primary" type="button" disabled={role !== 'admin' || decision.isPending} onClick={() => decision.mutate({ id: selected.id, choice: 'approved' })}><Check size={13} /> Approve version</button></div>
        </div></div>
    </div>}
  </div>
}
