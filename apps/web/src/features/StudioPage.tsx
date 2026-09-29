import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, CircleHelp, FileText, Layers3, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { messageOf } from '../lib/format'
import type { Role } from '../lib/types'
import { EmptyState, LoadingPanel, Notice } from '../components/Ui'
import { IntakeForm } from './IntakeForm'
import { BriefWorkspace } from './BriefWorkspace'
import { QuoteWorkspace } from './QuoteWorkspace'

export function StudioPage({ briefId, role, onBriefCreated }: { briefId?: string; role: Role; onBriefCreated: (id: string) => void }) {
  const client = useQueryClient()
  const [quoteId, setQuoteId] = useState('')
  const [selectedVersionId, setSelectedVersionId] = useState('')
  const brief = useQuery({ queryKey: ['brief', briefId], queryFn: () => api.getBrief(briefId!), enabled: !!briefId })
  const quote = useQuery({ queryKey: ['quote', quoteId], queryFn: () => api.getQuote(quoteId), enabled: !!quoteId })
  const generate = useMutation({
    mutationFn: () => api.generateOptions(briefId!),
    onSuccess: (value) => { setQuoteId(value.quote_id); setSelectedVersionId(value.options[1]?.id || value.options[0]?.id || ''); client.invalidateQueries({ queryKey: ['brief', briefId] }); client.invalidateQueries({ queryKey: ['quote', value.quote_id] }) },
  })
  useEffect(() => { setQuoteId(''); setSelectedVersionId('') }, [briefId])
  useEffect(() => { if (brief.data?.quote_id) setQuoteId(brief.data.quote_id) }, [brief.data?.quote_id])
  useEffect(() => {
    if (!quote.data?.versions.length || selectedVersionId) return
    const current = quote.data.versions.filter((version) => !['superseded', 'rejected'].includes(version.status))
    setSelectedVersionId(current.find((version) => version.label === 'Recommended')?.id || current.at(-1)?.id || quote.data.versions.at(-1)!.id)
  }, [quote.data, selectedVersionId])

  if (!briefId) return <IntakeForm onCreated={onBriefCreated} />
  if (brief.isPending) return <div className="page"><LoadingPanel label="Opening brief…" /></div>
  if (brief.isError) return <div className="page"><Notice tone="error" onRetry={() => brief.refetch()}>{messageOf(brief.error)}</Notice></div>
  const current = brief.data
  const openQuestions = current.clarifications?.filter((item) => !item.answer).length || 0
  const hasRequirements = !!current.requirements?.length
  const hasQuote = !!quoteId && !!quote.data?.versions.length
  const stage = hasQuote ? 3 : openQuestions ? 2 : hasRequirements ? 2 : 1

  return <div className="page">
    <div className="page-header"><div><div className="eyebrow">Arc & Field Studio / Proposal workspace</div><h1 className="page-title">{current.company_name ? `A proposal for ${current.company_name}.` : 'A new proposal takes shape.'}</h1><p className="page-subtitle">Work from the client’s words, make assumptions visible, and keep pricing grounded in the service catalog.</p></div>
      <div className="page-actions"><span className="badge">BRIEF {current.id.slice(0,8).toUpperCase()}</span><button type="button" className="btn btn-primary" disabled={role === 'viewer' || !hasRequirements || openQuestions > 0 || generate.isPending} title={!hasRequirements ? 'Analyze the brief first' : openQuestions ? 'Answer open clarifications first' : undefined} onClick={() => generate.mutate()}><Layers3 size={14} /> {generate.isPending ? 'Building options…' : hasQuote ? 'Regenerate options' : 'Generate 3 options'}</button></div>
    </div>
    <div className="flex items-center gap-2 sm:gap-4 mb-6 text-[10px] overflow-x-auto pb-2" aria-label="Proposal progress">
      {[['01','Intake'],['02','Clarify'],['03','Scope options'],['04','Review & share']].map(([number,label], index) => <div key={number} className={`flex items-center gap-2 whitespace-nowrap ${stage >= index + 1 ? 'text-[#b9745e]' : 'text-[#adb2a9]'}`}><span className={`w-6 h-6 rounded-full grid place-items-center text-[9px] font-bold ${stage > index + 1 ? 'bg-[#e9d6cc]' : stage === index + 1 ? 'bg-[#d2826b] text-white' : 'bg-[#eae8e2]'}`}>{stage > index + 1 ? <Check size={12} /> : number}</span><span className="font-semibold">{label}</span>{index < 3 && <span className="w-6 sm:w-10 h-[1px] bg-[#dedbd3] ml-1" />}</div>)}
    </div>
    {generate.isError && <div className="mb-5"><Notice tone="error">{messageOf(generate.error)}</Notice></div>}
    {openQuestions > 0 && <div className="mb-5"><Notice tone="info">{openQuestions} clarification{openQuestions === 1 ? '' : 's'} need an answer before new options can be generated. You can record the answer in the Brief & requirements panel or create a scoped customer link.</Notice></div>}
    <div className="studio-grid"><div className="studio-left"><BriefWorkspace brief={current} role={role} />
        <div className="soft-card p-5"><div className="flex items-center gap-2 text-[#bd7862]"><CircleHelp size={16} /><span className="eyebrow">Scope discipline</span></div><p className="serif text-[19px] mt-3 leading-[1.35]">Ask before assuming.</p><p className="text-[11px] text-[#80877d] leading-[1.65] mt-2">Requirements include evidence from the source brief. New answers can change only the sections they affect when you regenerate a version.</p></div>
      </div><div className="studio-right">
        {quote.isPending && quoteId ? <LoadingPanel label="Loading scope options…" /> : quote.isError ? <Notice tone="error" onRetry={() => quote.refetch()}>{messageOf(quote.error)}</Notice> : quote.data && selectedVersionId ? <QuoteWorkspace brief={current} quote={quote.data} selectedVersionId={selectedVersionId} onSelectVersion={setSelectedVersionId} role={role} /> :
          <div className="panel overflow-hidden"><div className="panel-header"><div className="flex items-center gap-2"><Sparkles size={16} className="text-coral" /><h2 className="panel-heading">Proposal canvas</h2></div><span className="eyebrow">02 / SCOPE</span></div>
            <EmptyState icon={<FileText size={22} strokeWidth={1.5} />} title={hasRequirements ? 'Ready for the three directions' : 'Start with the client’s words'} description={hasRequirements ? openQuestions ? 'Answer the open questions to build catalog-linked options with clear assumptions.' : 'Generate three distinct scope options. Each line will map to a versioned service and deterministic price rule.' : 'Analyze the original brief to identify deliverables, constraints, assets, and missing information before quoting.'} action={hasRequirements && openQuestions === 0 && <button type="button" className="btn btn-coral" disabled={role === 'viewer' || generate.isPending} onClick={() => generate.mutate()}>Generate options <ArrowRight size={13} /></button>} />
          </div>}
      </div></div>
  </div>
}
