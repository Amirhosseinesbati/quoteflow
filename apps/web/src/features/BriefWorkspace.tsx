import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, ClipboardList, Link2, MessageCircleQuestion, Plus, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { onTabKeyDown } from '../lib/tabs'
import { messageOf } from '../lib/format'
import type { Brief, Role } from '../lib/types'
import { EmptyState, Notice, StatusBadge } from '../components/Ui'

type Tab = 'brief' | 'requirements' | 'questions'

export function BriefWorkspace({ brief, role }: { brief: Brief; role: Role }) {
  const client = useQueryClient()
  const [tab, setTab] = useState<Tab>('brief')
  const [question, setQuestion] = useState('')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [portalLink, setPortalLink] = useState('')
  const [success, setSuccess] = useState('')
  const invalidate = () => client.invalidateQueries({ queryKey: ['brief', brief.id] })
  const analyze = useMutation({ mutationFn: () => api.analyzeBrief(brief.id), onSuccess: () => { invalidate(); setTab('requirements'); setSuccess('Brief analyzed. Review the evidence and confirm open questions.') } })
  const add = useMutation({ mutationFn: () => api.addClarification(brief.id, question.trim()), onSuccess: () => { setQuestion(''); invalidate(); setSuccess('Question added to this brief.') } })
  const answer = useMutation({ mutationFn: ({ id, text }: { id: string; text: string }) => api.answerClarification(brief.id, id, text), onSuccess: () => { invalidate(); setSuccess('Answer saved. Regenerate packages to include the new information.') } })
  const share = useMutation({ mutationFn: () => api.briefPortalLink(brief.id), onSuccess: (value) => { setPortalLink(new URL(`/portal/${encodeURIComponent(value.token)}`, window.location.origin).toString()); setSuccess('Scoped clarification link created. Share it with the demo customer locally.') } })
  const canEdit = role !== 'viewer'
  const openCount = brief.clarifications?.filter((item) => !item.answer).length || 0
  const error = analyze.error || add.error || answer.error || share.error

  return <section className="panel" aria-label="Source brief and requirements">
    <div className="panel-header"><div><div className="eyebrow">Source of truth</div><h2 className="panel-heading mt-1">Brief & requirements</h2></div><StatusBadge status={brief.status} /></div>
    <div className="studio-tabs" role="tablist" onKeyDown={onTabKeyDown} aria-label="Brief details">
      <button type="button" role="tab" tabIndex={tab === 'brief' ? 0 : -1} aria-selected={tab === 'brief'} className={`studio-tab ${tab === 'brief' ? 'active' : ''}`} onClick={() => setTab('brief')}>Original brief</button>
      <button type="button" role="tab" tabIndex={tab === 'requirements' ? 0 : -1} aria-selected={tab === 'requirements'} className={`studio-tab ${tab === 'requirements' ? 'active' : ''}`} onClick={() => setTab('requirements')}>Requirements <span className="text-[9px]">{brief.requirements?.length || 0}</span></button>
      <button type="button" role="tab" tabIndex={tab === 'questions' ? 0 : -1} aria-selected={tab === 'questions'} className={`studio-tab ${tab === 'questions' ? 'active' : ''}`} onClick={() => setTab('questions')}>Clarifications {openCount > 0 && <span className="text-coral">· {openCount}</span>}</button>
    </div>
    <div className="panel-body">
      {success && <div className="mb-4"><Notice tone="success">{success}</Notice></div>}
      {error && <div className="mb-4"><Notice tone="error">{messageOf(error)}</Notice></div>}
      {tab === 'brief' && <div>
        <div className="flex gap-2 flex-wrap mb-5"><div className="soft-card px-3 py-2 flex-1 min-w-[140px]"><div className="eyebrow">Client</div><div className="text-[11px] mt-1 font-semibold">{brief.company_name || 'Not supplied'}</div></div><div className="soft-card px-3 py-2 flex-1 min-w-[140px]"><div className="eyebrow">Contact</div><div className="text-[11px] mt-1 font-semibold">{brief.contact_name || 'Not supplied'}</div></div></div>
        <div className="eyebrow mb-2">Original wording</div><div className="brief-copy">{brief.text}</div>
        <div className="border-t border-soft pt-4 mt-5 flex justify-between items-center gap-3 flex-wrap"><span className="text-[10px] text-secondary">The source remains available for every decision.</span><button type="button" className="btn btn-small btn-primary" disabled={!canEdit || analyze.isPending} onClick={() => analyze.mutate()}><Sparkles size={12} /> {analyze.isPending ? 'Analyzing…' : brief.requirements?.length ? 'Reanalyze brief' : 'Analyze brief'}</button></div>
      </div>}
      {tab === 'requirements' && <div>
        {!brief.requirements?.length ? <EmptyState icon={<ClipboardList size={22} />} title="Requirements will appear here" description="Analyze the original brief to extract supported requirements with evidence from the client’s words." action={<button type="button" className="btn btn-coral" disabled={!canEdit || analyze.isPending} onClick={() => analyze.mutate()}>Analyze brief <ArrowRight size={13} /></button>} /> : <>
          <p className="text-[11px] leading-[1.55] text-secondary mb-2">Only traceable statements belong in scope. Vague wording becomes a clarification, not a binding promise.</p>
          {brief.requirements.map((item, index) => <div className="requirement-item" key={item.id}><div className="flex items-start gap-3"><div className="text-coral serif text-[17px] leading-none">{String(index + 1).padStart(2,'0')}</div><div className="min-w-0 flex-1"><div className="text-[11px] font-semibold leading-[1.55] text-secondary">{item.text}</div><div className="text-[9px] uppercase tracking-[.11em] text-secondary mt-1">{item.kind}</div>{item.evidence && <div className="evidence">“{item.evidence}”</div>}</div></div></div>)}
        </>}
      </div>}
      {tab === 'questions' && <div>
        {!brief.clarifications?.length ? <EmptyState icon={<MessageCircleQuestion size={22} />} title="Nothing to clarify yet" description="Add a focused question when the brief leaves a scope decision open." /> : brief.clarifications.map((item, index) => <div className="clarification-item" key={item.id}><div className="flex justify-between gap-3"><div className="clarification-number">Question {String(index + 1).padStart(2,'0')}</div><StatusBadge status={item.answer ? 'answered' : 'open'} /></div><h3 className="serif text-[18px] mt-2 mb-1">{item.question}</h3>
          {item.answer ? <div className="clarification-answer"><strong>Answer</strong><p className="mt-1">{item.answer}</p></div> : <form className="mt-3" onSubmit={(event) => { event.preventDefault(); if (answers[item.id]?.trim()) answer.mutate({ id: item.id, text: answers[item.id].trim() }) }}><label htmlFor={`answer-${item.id}`} className="sr-only">Answer to {item.question}</label><textarea id={`answer-${item.id}`} className="textarea" rows={2} placeholder="Record the client’s answer…" value={answers[item.id] || ''} onChange={(event) => setAnswers({ ...answers, [item.id]: event.target.value })} disabled={!canEdit} /><button className="btn btn-small mt-2" type="submit" disabled={!canEdit || !answers[item.id]?.trim() || answer.isPending}>Save answer</button></form>}
        </div>)}
        <form className="border-t border-soft pt-4 mt-4" onSubmit={(event) => { event.preventDefault(); if (question.trim()) add.mutate() }}><label htmlFor="new-question" className="field"><span className="text-[10px] font-bold text-secondary">ADD A TARGETED QUESTION</span></label><textarea id="new-question" className="textarea mt-2" rows={2} placeholder="What should we confirm before finalizing the scope?" value={question} onChange={(event) => setQuestion(event.target.value)} disabled={!canEdit} /><div className="flex items-center gap-2 mt-3 flex-wrap"><button className="btn btn-small btn-primary" type="submit" disabled={!canEdit || !question.trim() || add.isPending}><Plus size={12} /> Add question</button><button className="btn btn-small" type="button" disabled={!canEdit || share.isPending} onClick={() => share.mutate()}><Link2 size={12} /> Create customer link</button></div></form>
        {portalLink && <div className="mt-4 soft-card p-3"><div className="eyebrow mb-2">Scoped customer link</div><a href={portalLink} target="_blank" rel="noreferrer" className="text-[11px] text-coral break-all underline">{portalLink}</a><button type="button" className="btn btn-small mt-2" onClick={() => navigator.clipboard.writeText(portalLink)}>Copy link</button></div>}
      </div>}
    </div>
  </section>
}
