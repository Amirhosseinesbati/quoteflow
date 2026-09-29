import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownToLine, ArrowRight, Check, ChevronDown, GitCompareArrows, Link2, Pencil, Plus, Printer, Send, Sparkles, Trash2 } from 'lucide-react'
import { api } from '../lib/api'
import { messageOf, money } from '../lib/format'
import type { Brief, Proposal, ProposalField, Quote, QuoteLine, QuoteLineEdit, QuoteVersion, Role } from '../lib/types'
import { proposalFields, ProposalPaper } from '../components/ProposalPaper'
import { EmptyState, Notice, StatusBadge } from '../components/Ui'

type PanelTab = 'preview' | 'edit' | 'diff'
const allFields: Array<[ProposalField, string]> = [['executive_summary', 'Executive summary'], ...proposalFields]
const editableText = (value: string | string[] | undefined) => Array.isArray(value) ? value.join('\n') : value || ''
const optionLabels = ['Essential', 'Recommended', 'Comprehensive']

function latestOptionSet(versions: QuoteVersion[]) {
  const ordered = [...versions].sort((left, right) => left.number - right.number)
  for (let index = ordered.length - 3; index >= 0; index -= 1) {
    const candidate = ordered.slice(index, index + 3)
    if (candidate.every((version, offset) => version.label === optionLabels[offset] && version.number === candidate[0].number + offset)) return candidate
  }
  return ordered.slice(0, 3)
}

function OptionCards({ versions, selected, onSelect }: { versions: QuoteVersion[]; selected: string; onSelect: (id: string) => void }) {
  return <div className="option-grid" role="group" aria-label="Scope options">
    {versions.map((version, index) => <button type="button" key={version.id} className={`option-card ${selected === version.id ? 'selected' : ''}`} aria-pressed={selected === version.id} onClick={() => onSelect(version.id)}>
      <span className="eyebrow">Option {String(index + 1).padStart(2,'0')}{index === 1 ? ' · RECOMMENDED' : ''}</span>
      <div className="option-name">{version.label || ['Essential','Signature','Complete'][index]}</div>
      <div className="text-[10px] text-[#8b9188] leading-[1.45] min-h-[27px]">{version.lines.length} catalog services · {version.approval_required ? 'Review required' : 'Ready to refine'}</div>
      <div className="option-price">{money(version.total)} <small>estimated investment</small></div>
      <div className="border-t border-[#efede7] mt-4 pt-2">{version.lines.slice(0, 3).map((line) => <div key={line.id} className="option-line"><Check size={11} className="text-[#92a08d] shrink-0 mt-[1px]" />{line.service_name}</div>)}{version.lines.length > 3 && <div className="option-line">+ {version.lines.length - 3} more services</div>}</div>
    </button>)}
  </div>
}

function ScopeDiff({ quote, selected }: { quote: Quote; selected: QuoteVersion }) {
  const [compareId, setCompareId] = useState('')
  const fallback = quote.versions.find((version) => version.id !== selected.id)
  const from = compareId && compareId !== selected.id ? compareId : fallback?.id
  const diff = useQuery({ queryKey: ['quote-diff', quote.id, from, selected.id], queryFn: () => api.quoteDiff(quote.id, from!, selected.id), enabled: !!from })
  if (!from) return <EmptyState icon={<GitCompareArrows size={22} />} title="A baseline is needed" description="A second quote version will make scope and price changes visible here." />
  return <div className="p-5">
    <div className="flex flex-wrap items-end gap-3 mb-5"><div className="field flex-1 min-w-[180px]"><label htmlFor="compare-version">COMPARE AGAINST</label><select id="compare-version" className="select" value={from} onChange={(event) => setCompareId(event.target.value)}>{quote.versions.filter((version) => version.id !== selected.id).map((version) => <option key={version.id} value={version.id}>Version {version.number} · {version.label}</option>)}</select></div><span className="text-[11px] text-[#8b9288] pb-2">→ Version {selected.number}</span></div>
    {diff.isPending ? <div className="skeleton h-[140px]" /> : diff.isError ? <Notice tone="error" onRetry={() => diff.refetch()}>{messageOf(diff.error)}</Notice> : <>
      <div className="soft-card p-4 mb-4 flex justify-between items-center gap-3"><div><div className="eyebrow">Total change</div><div className="serif text-[26px] mt-1">{Number(diff.data.total_delta) >= 0 ? '+' : ''}{money(diff.data.total_delta)}</div></div><GitCompareArrows size={22} className="text-[#c98b75]" /></div>
      {([['Added services', diff.data.added_lines], ['Removed services', diff.data.removed_lines]] as Array<[string, string[]]>).map(([title, names]) => <section key={title} className="mb-4"><div className="eyebrow mb-2">{title}</div>{names.length ? names.map((name) => <div key={name} className="soft-card p-3 text-[11px] mb-2">{name}</div>) : <p className="text-[11px] text-[#a0a69d]">None</p>}</section>)}
      {diff.data.changed_lines.length > 0 && <section className="mb-4"><div className="eyebrow mb-2">Changed services</div>{diff.data.changed_lines.map((change) => <div key={change.service} className="soft-card p-3 text-[11px] mb-2"><strong>{change.service.replace(/[_-]/g, ' ')}</strong><div className="text-[#868d83] mt-1">{change.old_quantity} → {change.new_quantity} · {money(change.old_total)} → {money(change.new_total)}</div></div>)}</section>}
      <section><div className="eyebrow mb-2">Proposal language changed</div>{diff.data.proposal_changes.length ? <div className="flex gap-2 flex-wrap">{diff.data.proposal_changes.map((field) => <span className="badge" key={field}>{field.replace(/_/g,' ')}</span>)}</div> : <p className="text-[11px] text-[#a0a69d]">None</p>}</section>
    </>}
  </div>
}

export function QuoteWorkspace({ brief, quote, selectedVersionId, onSelectVersion, role }: { brief: Brief; quote: Quote; selectedVersionId: string; onSelectVersion: (id: string) => void; role: Role }) {
  const client = useQueryClient()
  const selected = quote.versions.find((version) => version.id === selectedVersionId) || quote.versions[0]
  const [tab, setTab] = useState<PanelTab>('preview')
  const [draft, setDraft] = useState<Proposal>(selected?.proposal)
  const [lines, setLines] = useState<QuoteLine[]>(selected?.lines || [])
  const [discount, setDiscount] = useState(selected?.discount_percent || '0')
  const [tax, setTax] = useState(selected?.tax_percent || '0')
  const [contingency, setContingency] = useState(selected?.contingency_percent || '0')
  const [serviceId, setServiceId] = useState('')
  const [portalLink, setPortalLink] = useState('')
  const [success, setSuccess] = useState('')
  const catalog = useQuery({ queryKey: ['catalog'], queryFn: api.getCatalog, enabled: tab === 'edit' })
  useEffect(() => { if (selected) { setDraft(selected.proposal); setLines(selected.lines); setDiscount(selected.discount_percent || '0'); setTax(selected.tax_percent || '0'); setContingency(selected.contingency_percent || '0') } }, [selected?.id])
  const changed = useMemo(() => selected && (JSON.stringify(draft) !== JSON.stringify(selected.proposal) || JSON.stringify(lines) !== JSON.stringify(selected.lines) || discount !== selected.discount_percent || tax !== selected.tax_percent || contingency !== selected.contingency_percent), [selected, draft, lines, discount, tax, contingency])
  const canEdit = role !== 'viewer' && !['accepted','superseded'].includes(selected?.status || '')
  const lineEdits = (): QuoteLineEdit[] => lines.map((line) => ({ service_id: line.service_id, service_name: line.service_name, quantity: String(line.quantity), assumption: line.assumption }))
  const save = useMutation({ mutationFn: () => api.updateVersion(quote.id, selected.id, { proposal: draft, lines: lineEdits(), discount_percent: discount, tax_percent: tax, contingency_percent: contingency }),
    onSuccess: (version) => { client.invalidateQueries({ queryKey: ['quote', quote.id] }); client.invalidateQueries({ queryKey: ['brief', brief.id] }); onSelectVersion(version.id); setTab('preview'); setSuccess(`Version ${version.number} saved. Earlier approval no longer applies to changed scope or price.`) },
  })
  const preview = useMutation({ mutationFn: () => api.pricePreview(quote.id, selected.id, { lines: lineEdits(), discount_percent: discount, tax_percent: tax, contingency_percent: contingency }), onSuccess: () => setSuccess('Pricing preview calculated by the server. Save a new version to commit changes.') })
  const submit = useMutation({ mutationFn: () => api.submitReview(quote.id, selected.id), onSuccess: () => { client.invalidateQueries({ queryKey: ['quote', quote.id] }); client.invalidateQueries({ queryKey: ['approvals'] }); setSuccess('This exact quote version was sent to the internal review queue.') } })
  const publish = useMutation({ mutationFn: () => api.publishVersion(quote.id, selected.id), onSuccess: (value) => { setPortalLink(new URL(`/portal/${encodeURIComponent(value.token)}`, window.location.origin).toString()); client.invalidateQueries({ queryKey: ['quote', quote.id] }); setSuccess('PDF generated and a scoped customer review link created. Demo notification was recorded in the outbox only.') } })
  if (!selected) return <EmptyState title="No quote versions" description="Generate scope options to begin." />
  const error = save.error || preview.error || submit.error || publish.error
  const pdfUrl = api.pdfUrl(quote.id, selected.id)
  const activeServices = catalog.data?.services.filter((service) => service.active && !lines.some((line) => line.service_id === service.id)) || []
  const optionVersions = latestOptionSet(quote.versions)
  const revisionVersions = quote.versions.filter((version) => !optionVersions.some((option) => option.id === version.id))

  return <>
    <div className="mb-3 flex justify-between items-end gap-3 flex-wrap"><div><div className="eyebrow">03 / COMPARE</div><div className="serif text-[23px] mt-1">Three ways forward.</div></div><span className="text-[10px] text-[#91978e]">Select a package to inspect its scope and price.</span></div>
    <OptionCards versions={optionVersions} selected={selected.id} onSelect={onSelectVersion} />
    {revisionVersions.length > 0 && <div className="flex items-center gap-2 mb-5 flex-wrap"><span className="eyebrow">Other versions</span>{revisionVersions.map((version) => <button key={version.id} type="button" className={`btn btn-small ${selected.id === version.id ? 'btn-coral' : ''}`} onClick={() => onSelectVersion(version.id)}>v{version.number} · {version.label}</button>)}</div>}
    {success && <div className="mb-4"><Notice tone="success">{success}</Notice></div>}
    {error && <div className="mb-4"><Notice tone="error">{messageOf(error)}</Notice></div>}
    <div className="panel overflow-hidden"><div className="panel-header flex-wrap"><div className="flex items-center gap-3"><div><div className="eyebrow">Selected proposal</div><div className="panel-heading mt-1">{selected.label} <span className="text-[11px] font-sans text-[#9da399]">/ v{selected.number}</span></div></div><StatusBadge status={selected.status} /></div>
      <div className="proposal-toolbar"><button type="button" className="btn btn-small" onClick={() => window.print()}><Printer size={12} /> Print</button><a className="btn btn-small" href={pdfUrl} target="_blank" rel="noreferrer"><ArrowDownToLine size={12} /> PDF</a></div>
    </div>
    <div className="studio-tabs" role="tablist" aria-label="Proposal views"><button type="button" className={`studio-tab ${tab === 'preview' ? 'active' : ''}`} role="tab" aria-selected={tab === 'preview'} onClick={() => setTab('preview')}>Document preview</button><button type="button" className={`studio-tab ${tab === 'edit' ? 'active' : ''}`} role="tab" aria-selected={tab === 'edit'} onClick={() => setTab('edit')}><Pencil size={11} className="inline mr-1" /> Edit scope & price</button><button type="button" className={`studio-tab ${tab === 'diff' ? 'active' : ''}`} role="tab" aria-selected={tab === 'diff'} onClick={() => setTab('diff')}><GitCompareArrows size={11} className="inline mr-1" /> Scope diff</button></div>
    {tab === 'preview' && <div className="p-3 sm:p-5 bg-[#f4f2ed]"><ProposalPaper version={selected} brief={brief} /></div>}
    {tab === 'diff' && <ScopeDiff quote={quote} selected={selected} />}
    {tab === 'edit' && <div className="p-5"><div className="alert info mb-5"><Sparkles size={14} className="shrink-0 mt-[2px]" /><span>Saving creates a new quote version. Amounts and policy checks are computed by the server from catalog rules.</span></div>
      <div className="edit-grid">{allFields.map(([field,label]) => <div className="field" key={field}><label htmlFor={`proposal-${field}`}>{label.toUpperCase()}</label><textarea id={`proposal-${field}`} className="textarea" rows={field === 'executive_summary' || field === 'scope' ? 4 : 2} value={editableText(draft?.[field])} disabled={!canEdit} onChange={(event) => setDraft({ ...draft, [field]: Array.isArray(draft?.[field]) ? event.target.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean) : event.target.value })} /></div>)}</div>
      <div className="border-t border-[#ebe8e0] mt-6 pt-6"><div className="flex items-end justify-between gap-3 flex-wrap mb-4"><div><div className="eyebrow">Catalog linked</div><h3 className="serif text-[23px] mt-1">Line items</h3></div><span className="text-[10px] text-[#9aa198]">Rates are set in the service catalog</span></div>
        <div className="space-y-3">{lines.map((line, index) => <div key={line.id || `${line.service_id}-${index}`} className="soft-card p-3"><div className="flex justify-between gap-3 mb-3"><div><strong className="text-[11px]">{line.service_name}</strong><div className="text-[10px] text-[#969d93] mt-1">{money(line.unit_price)} / unit</div></div><button type="button" className="icon-btn !min-w-[28px] !min-h-[28px]" title="Remove line" aria-label={`Remove ${line.service_name}`} disabled={!canEdit} onClick={() => setLines(lines.filter((_, position) => position !== index))}><Trash2 size={12} /></button></div><div className="grid grid-cols-[90px_1fr] gap-2"><div className="field"><label htmlFor={`line-qty-${index}`}>QUANTITY</label><input id={`line-qty-${index}`} className="input" type="number" min="0.01" step="0.01" value={line.quantity} disabled={!canEdit} onChange={(event) => setLines(lines.map((item, position) => position === index ? { ...item, quantity: event.target.value } : item))} /></div><div className="field"><label htmlFor={`line-note-${index}`}>SCOPE ASSUMPTION</label><input id={`line-note-${index}`} className="input" value={line.assumption} disabled={!canEdit} onChange={(event) => setLines(lines.map((item, position) => position === index ? { ...item, assumption: event.target.value } : item))} /></div></div></div>)}</div>
        <div className="flex gap-2 mt-3"><select aria-label="Add catalog service" className="select flex-1" value={serviceId} onChange={(event) => setServiceId(event.target.value)} disabled={!canEdit}><option value="">Select a catalog service…</option>{activeServices.map((service) => <option key={service.id} value={service.id}>{service.name} · {money(service.base_price)}</option>)}</select><button type="button" className="btn" disabled={!canEdit || !serviceId} onClick={() => { const service = activeServices.find((item) => item.id === serviceId); if (!service) return; setLines([...lines, { id: crypto.randomUUID(), service_id: service.id, service_name: service.name, quantity: '1', unit_price: service.base_price, assumption: 'One catalog unit as described in the scope.', line_total: service.base_price }]); setServiceId('') }}><Plus size={13} /> Add</button></div>
      </div>
      <div className="border-t border-[#ebe8e0] mt-6 pt-6"><div className="eyebrow mb-4">Pricing policy</div><div className="grid grid-cols-1 sm:grid-cols-3 gap-3"><div className="field"><label htmlFor="discount">DISCOUNT %</label><input id="discount" className="input" type="number" min="0" max="100" step="0.01" value={discount} disabled={!canEdit} onChange={(event) => setDiscount(event.target.value)} /></div><div className="field"><label htmlFor="tax">TAX %</label><input id="tax" className="input" type="number" min="0" max="100" step="0.01" value={tax} disabled={!canEdit} onChange={(event) => setTax(event.target.value)} /></div><div className="field"><label htmlFor="contingency">CONTINGENCY %</label><input id="contingency" className="input" type="number" min="0" max="100" step="0.01" value={contingency} disabled={!canEdit} onChange={(event) => setContingency(event.target.value)} /></div></div>
        <div className="flex flex-wrap gap-2 mt-4"><button type="button" className="btn" disabled={!canEdit || preview.isPending} onClick={() => preview.mutate()}><ChevronDown size={13} /> {preview.isPending ? 'Calculating…' : 'Preview price'}</button><button type="button" className="btn btn-primary" disabled={!canEdit || !changed || save.isPending} onClick={() => save.mutate()}>{save.isPending ? 'Saving…' : 'Save as new version'} <ArrowRight size={13} /></button></div>
        {preview.data && <div className="soft-card p-4 mt-4"><div className="eyebrow mb-3">Server-calculated preview</div><div className="grid grid-cols-2 gap-y-2 text-[11px]"><span>Subtotal</span><strong className="text-right">{money(preview.data.subtotal)}</strong><span>Discount</span><strong className="text-right">−{money(preview.data.discount_amount)}</strong><span>Tax + contingency</span><strong className="text-right">{money(Number(preview.data.tax_amount) + Number(preview.data.contingency_amount))}</strong><span className="border-t border-[#dad7ce] pt-3 font-bold">Total</span><strong className="border-t border-[#dad7ce] pt-3 text-right text-[15px]">{money(preview.data.total)}</strong></div>{preview.data.approval_required && <div className="text-[10px] text-[#b27054] mt-3">This price requires internal approval.</div>}</div>}
      </div>
    </div>}
    <div className="border-t border-[#e9e5dd] bg-[#faf9f6] p-4 flex items-center justify-between gap-3 flex-wrap"><div><div className="eyebrow">Ready to progress?</div><div className="text-[10px] text-[#828a7f] mt-1">{selected.approval_required ? selected.approved ? 'Approved version can be shared.' : 'Internal review is required before sharing.' : 'This version can be shared after your final check.'}</div></div><div className="flex flex-wrap gap-2">
      {selected.approval_required && !selected.approved && <button type="button" className="btn" disabled={!canEdit || submit.isPending} onClick={() => submit.mutate()}><Send size={12} /> {submit.isPending ? 'Submitting…' : 'Request approval'}</button>}
      <button type="button" className="btn btn-coral" disabled={!canEdit || (selected.approval_required && !selected.approved) || publish.isPending} onClick={() => publish.mutate()}><Link2 size={12} /> {publish.isPending ? 'Publishing…' : 'Generate PDF & review link'}</button>
    </div></div>
    {portalLink && <div className="p-4 bg-[#f4faf3] border-t border-[#d7e6d4]"><div className="eyebrow mb-2">Version-bound customer link</div><div className="flex items-center gap-3 flex-wrap"><a href={portalLink} target="_blank" rel="noreferrer" className="text-[11px] text-[#52765a] underline break-all">{portalLink}</a><button type="button" className="btn btn-small" onClick={() => navigator.clipboard.writeText(portalLink)}>Copy link</button></div><p className="text-[10px] text-[#84978a] mt-2">Published version {selected.number}. Demo notification is recorded in the local outbox.</p></div>}
    </div>
  </>
}
