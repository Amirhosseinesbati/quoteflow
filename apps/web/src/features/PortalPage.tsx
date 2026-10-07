import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, ChevronRight, MessageCircleQuestion, Sparkles, X } from 'lucide-react'
import { api } from '../lib/api'
import { ThemeControl } from '../lib/theme'
import { messageOf, shortDate } from '../lib/format'
import { ProposalPaper } from '../components/ProposalPaper'
import { Dialog, EmptyState, LoadingPanel, Notice, StatusBadge } from '../components/Ui'

function ClarificationPortal({ token }: { token: string }) {
  const client = useQueryClient()
  const portal = useQuery({ queryKey: ['portal', token], queryFn: () => api.getPortal(token) })
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [success, setSuccess] = useState('')
  const answer = useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) => api.portalAnswer(token, id, text),
    onSuccess: () => { setSuccess('Your answer was saved. The studio can now revise the relevant scope.'); client.invalidateQueries({ queryKey: ['portal', token] }) },
  })
  if (portal.isPending) return <div className="portal-main"><LoadingPanel label="Opening your questions…" /></div>
  if (portal.isError) return <div className="portal-main"><Notice tone="error" onRetry={() => portal.refetch()}>{messageOf(portal.error)} The link may be expired or replaced.</Notice></div>
  if (portal.data.kind !== 'clarification') return <ReviewPortal token={token} />
  const data = portal.data
  return <div className="portal-main"><div className="eyebrow">Project discovery</div><h1 className="page-title">A few thoughtful questions.</h1><p className="page-subtitle max-w-[650px]">Thanks for sharing your brief. These details help us shape an accurate scope and avoid assumptions about your project.</p>
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(245px,.38fr)] max-[800px]:grid-cols-1 gap-5 mt-7 items-start">
      <section className="panel"><div className="panel-header"><div className="panel-heading">For {data.brief.company_name || 'your team'}</div>{portal.data?.synthetic !== false && <span className="badge coral">SYNTHETIC DEMO</span>}</div><div className="panel-body">
        {success && <div className="mb-4"><Notice tone="success">{success}</Notice></div>}
        {answer.isError && <div className="mb-4"><Notice tone="error">{messageOf(answer.error)}</Notice></div>}
        {data.clarifications.length === 0 ? <EmptyState icon={<MessageCircleQuestion size={22} />} title="All clear for now" description="No questions are waiting for your answer." /> : data.clarifications.map((item, index) => <div className="clarification-item" key={item.id}>
          <div className="clarification-number">Question {String(index + 1).padStart(2,'0')}</div><h2 className="serif text-[19px] mt-2 mb-3">{item.question}</h2>
          {item.answer ? <div className="clarification-answer"><strong>Answer recorded</strong><p className="mt-1">{item.answer}</p></div> : <form onSubmit={(event) => { event.preventDefault(); if (answers[item.id]?.trim()) answer.mutate({ id: item.id, text: answers[item.id].trim() }) }}><label className="field" htmlFor={`answer-${item.id}`}><span className="text-[10px] font-bold text-secondary">YOUR ANSWER</span></label><textarea className="textarea mt-2" id={`answer-${item.id}`} rows={3} value={answers[item.id] || ''} onChange={(event) => setAnswers({ ...answers, [item.id]: event.target.value })} placeholder="Share the specifics you know so far…" required /><button className="btn btn-primary mt-3" type="submit" disabled={answer.isPending}>Save answer <ArrowRight size={13} /></button></form>}
        </div>)}
      </div></section>
      <aside className="soft-card p-5 text-[11px] leading-[1.65] text-secondary"><div className="eyebrow mb-3">About this link</div><p>Only answers to these questions are collected here. Your quotation will be shared through a separate review link when it is ready.</p><p className="mt-4">Link expires: {shortDate(data.expires_at)}</p>{data.synthetic !== false && <p className="mt-4 text-secondary">This is a synthetic product demonstration.</p>}</aside>
    </div>
  </div>
}

function ReviewPortal({ token }: { token: string }) {
  const client = useQueryClient()
  const portal = useQuery({ queryKey: ['portal', token], queryFn: () => api.getPortal(token) })
  const [choice, setChoice] = useState<'accepted' | 'declined' | 'revision_requested' | null>(null)
  const [comment, setComment] = useState('')
  const [handoff, setHandoff] = useState('')
  const response = useMutation({
    mutationFn: (decision: 'accepted' | 'declined' | 'revision_requested') => api.portalRespond(token, decision, comment.trim() || undefined),
    onSuccess: (value) => { setHandoff(value.handoff_id || ''); setChoice(null); client.invalidateQueries({ queryKey: ['portal', token] }) },
  })
  if (portal.isPending) return <div className="portal-main"><LoadingPanel label="Opening proposal…" /></div>
  if (portal.isError) return <div className="portal-main"><Notice tone="error" onRetry={() => portal.refetch()}>{messageOf(portal.error)} The link may be expired or replaced.</Notice></div>
  if (portal.data.kind !== 'review') return <ClarificationPortal token={token} />
  const data = portal.data
  const closed = ['accepted','declined','revision_requested','expired','replaced','revoked'].includes(data.status)
  return <div className="portal-main"><div className="flex items-center gap-2 text-[10px] text-secondary uppercase tracking-[.12em] mb-3">Client review <ChevronRight size={12} /> {data.client_name}</div>
    <div className="flex flex-wrap justify-between items-end gap-4 mb-6"><div><h1 className="page-title">A proposal, just for you.</h1><p className="page-subtitle">Review the scope and investment below, then let us know how you would like to proceed.</p></div><StatusBadge status={data.status} /></div>
    <div className="portal-grid"><ProposalPaper version={data.quote_version} clientName={data.client_name} />
      <aside className="portal-aside"><div className="panel"><div className="panel-header"><div className="panel-heading">Your decision</div></div><div className="panel-body">
        <p className="text-[11px] text-secondary leading-[1.65] mb-5">This review is for version {data.quote_version.number} only. You can request changes before accepting.</p>
        {handoff && <div className="mb-4"><Notice tone="success">Project handoff created: {handoff}</Notice></div>}
        {closed ? <Notice tone={data.status === 'accepted' ? 'success' : 'info'}>This review is {data.status.replace(/_/g,' ')}. The link cannot accept a different quote version.</Notice> : <div className="portal-actions">
          <button type="button" className="btn btn-primary" onClick={() => setChoice('accepted')}><Check size={14} /> Accept proposal</button>
          <button type="button" className="btn" onClick={() => setChoice('revision_requested')}><MessageCircleQuestion size={14} /> Request revisions</button>
          <button type="button" className="btn btn-ghost" onClick={() => setChoice('declined')}><X size={14} /> Decline</button>
        </div>}
        <div className="page-stamp mt-6">Expires {shortDate(data.expires_at)}. Acceptance records a product workflow acknowledgement; it is not a certified electronic signature.</div>
        {response.isError && <div className="mt-4"><Notice tone="error">{messageOf(response.error)}</Notice></div>}
      </div></div></aside>
    </div>
    {choice && <Dialog labelId="response-title" onClose={() => { if (!response.isPending) setChoice(null) }}>
      <div className="panel-header"><h2 id="response-title" className="serif text-[24px]">{choice === 'accepted' ? 'Accept this version?' : choice === 'declined' ? 'Decline proposal?' : 'Request a revision'}</h2><button type="button" className="icon-btn" aria-label="Close response" disabled={response.isPending} onClick={() => setChoice(null)}><X size={15} /></button></div><div className="panel-body">
        <p className="text-[12px] text-secondary leading-[1.6] mb-4">{choice === 'accepted' ? 'The current version will be frozen and a project handoff created for the studio.' : 'Your response will be recorded for the studio to review.'}</p>
        <div className="field"><label htmlFor="portal-comment">{choice === 'revision_requested' ? 'WHAT WOULD YOU LIKE CHANGED?' : 'OPTIONAL NOTE'}</label><textarea id="portal-comment" className="textarea" rows={4} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Add context for your response…" /></div>
        {response.isError && <div className="mt-4"><Notice tone="error">{messageOf(response.error)}</Notice></div>}<div className="flex justify-end gap-2 mt-5"><button type="button" className="btn" onClick={() => setChoice(null)}>Cancel</button><button type="button" className="btn btn-primary" disabled={response.isPending || (choice === 'revision_requested' && !comment.trim())} onClick={() => response.mutate(choice)}>{response.isPending ? 'Saving…' : 'Confirm response'}</button></div>
      </div></Dialog>}
  </div>
}

export function PortalPage({ token }: { token: string }) {
  const portal = useQuery({ queryKey: ['portal', token], queryFn: () => api.getPortal(token), retry: false })
  return <div className="portal-shell"><header className="portal-top"><div className="flex items-center gap-2"><span className="brand-mark !w-[29px] !h-[29px]"><Sparkles size={16} /></span><span className="brand-word !text-[18px]">Quote<span>Flow</span></span></div><div className="flex items-center gap-2"><ThemeControl />{portal.data?.synthetic !== false && <span className="badge coral">SYNTHETIC DEMO</span>}<span className="text-[10px] text-secondary hidden sm:inline">{portal.data?.kind === 'review' ? portal.data.quote_version.proposal?._document?.studio_name || 'Arc & Field Studio' : portal.data?.studio_name || 'Arc & Field Studio'}</span></div></header>
    {portal.isPending ? <div className="portal-main"><LoadingPanel label="Verifying your link…" /></div> : portal.isError ? <div className="portal-main"><EmptyState title="This link is unavailable" description="It may have expired, been replaced, or belong to another client. Ask the studio for a current link." action={<button type="button" className="btn" onClick={() => portal.refetch()}>Try again</button>} /></div> : portal.data.kind === 'clarification' ? <ClarificationPortal token={token} /> : <ReviewPortal token={token} />}
  </div>
}
