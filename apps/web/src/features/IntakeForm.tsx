import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight, FileText, Mail, Paperclip } from 'lucide-react'
import { api } from '../lib/api'
import { messageOf } from '../lib/format'
import { Notice } from '../components/Ui'
import { useStudio } from '../lib/studio'

export function IntakeForm({ onCreated, readOnly = false }: { onCreated: (id: string) => void; readOnly?: boolean }) {
  const studio = useStudio()
  const [source, setSource] = useState<'paste' | 'form' | 'pdf'>('paste')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [company, setCompany] = useState('')
  const [contact, setContact] = useState('')
  const [email, setEmail] = useState('')
  const create = useMutation({
    mutationFn: () => source === 'pdf' && file ? api.uploadBrief(file) : api.createBrief({ source_type: source === 'pdf' ? 'paste' : source, text: text.trim(), company_name: company.trim() || undefined, contact_name: contact.trim() || undefined, contact_email: email.trim() || undefined }),
    onSuccess: (brief) => onCreated(brief.id),
  })
  const valid = !readOnly && (source === 'pdf' ? !!file && file.size <= 5_000_000 && file.type === 'application/pdf' : text.trim().length >= 20)

  return <div className="page">
    {readOnly && <div className="mb-4"><Notice>Viewer access is read only. Open an existing brief to inspect proposals.</Notice></div>}
    <div className="page-header"><div><div className="eyebrow">01 / NEW PROJECT</div><h1 className="page-title">Start with the source.</h1><p className="page-subtitle max-w-[590px]">Capture the client’s words. Extract the requirements, resolve the unknowns, then build three catalog-backed proposals.</p></div>{studio.synthetic && <span className="badge coral">SYNTHETIC DEMO DATA</span>}</div>
    <div className="studio-grid intake-grid">
      <section className="panel"><div className="panel-header"><div className="flex items-center gap-2"><span className="text-coral"><FileText size={17} /></span><h2 className="panel-heading">Start with a client brief</h2></div><span className="eyebrow">01 / INTAKE</span></div>
        <form className="panel-body" onSubmit={(event) => { event.preventDefault(); if (valid) create.mutate() }}>
          <div className="flex gap-2 mb-5 flex-wrap" role="group" aria-label="Brief source"><button type="button" className={`btn ${source === 'paste' ? 'btn-primary' : ''}`} aria-pressed={source === 'paste'} onClick={() => setSource('paste')}><Mail size={13} /> Pasted email</button><button type="button" className={`btn ${source === 'form' ? 'btn-primary' : ''}`} aria-pressed={source === 'form'} onClick={() => setSource('form')}><FileText size={13} /> Demo form</button><button type="button" className={`btn ${source === 'pdf' ? 'btn-primary' : ''}`} aria-pressed={source === 'pdf'} onClick={() => setSource('pdf')}><Paperclip size={13} /> PDF brief</button></div>
          {source === 'pdf' ? <div className="field mb-5"><label htmlFor="brief-file">PDF ATTACHMENT *</label><input id="brief-file" type="file" accept="application/pdf,.pdf" className="input !py-4" onChange={(event) => setFile(event.target.files?.[0] || null)} /><span className="field-help">PDF only, maximum 5 MB. The file is validated by the API; extracted text becomes the source brief.</span>{file && file.size > 5_000_000 && <span className="text-[10px] text-secondary">This file is larger than 5 MB.</span>}</div> : <>
            <div className="field mb-5"><label htmlFor="brief-text">CLIENT NOTE OR PROJECT BRIEF *</label><textarea id="brief-text" className="textarea min-h-[250px]" value={text} onChange={(event) => setText(event.target.value)} placeholder={'Hi, we are refreshing our brand and need a new website by October. We have some photography, but no content yet. Could you include a few options? Our rough budget is…'} required minLength={20} /><span className="field-help">Include the original wording. Evidence is kept alongside every extracted requirement.</span></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4"><div className="field"><label htmlFor="company">COMPANY (OPTIONAL)</label><input id="company" className="input" value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Client company" /></div><div className="field"><label htmlFor="contact">CONTACT NAME (OPTIONAL)</label><input id="contact" className="input" value={contact} onChange={(event) => setContact(event.target.value)} placeholder="Client contact" /></div></div>
            <div className="field mb-5"><label htmlFor="email">CONTACT EMAIL (OPTIONAL)</label><input id="email" className="input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" /><span className="field-help">{studio.synthetic ? 'Demo mode records notifications locally; no email is sent.' : 'Notification delivery is tracked separately from proposal publication.'}</span></div>
          </>}
          {create.isError && <div className="mb-4"><Notice tone="error">{messageOf(create.error)}</Notice></div>}
          <div className="flex items-center justify-between gap-3 flex-wrap border-t border-soft pt-5"><span className="text-[10px] text-secondary">{source === 'pdf' ? 'PDF · 5 MB maximum' : '20 character minimum'} · Review before pricing</span><button type="submit" className="btn btn-coral" disabled={!valid || create.isPending}>{create.isPending ? 'Saving brief…' : 'Create brief'} <ArrowRight size={14} /></button></div>
        </form>
      </section>
      <aside className="studio-right" aria-label="Proposal workflow context">
        <div className="panel"><div className="panel-header"><div className="panel-heading">The path to a proposal</div><span className="eyebrow">4 STAGES</span></div><ol className="pipeline-list">{[['01', 'Intake → evidence', 'Keep the original note. Each requirement points back to the source.'], ['02', 'Clarify → confidence', 'Ask targeted questions before committing to scope or price.'], ['03', 'Options → exact numbers', 'Compare three packages linked to versioned catalog rates.'], ['04', 'Review → handoff', 'Approve an exact version, export its PDF, and record the client’s response.']].map(([number,title,detail]) => <li key={number}><span className="pipeline-number">{number}</span><div><h3>{title}</h3><p>{detail}</p></div></li>)}</ol></div>
        <div className="soft-card p-5"><div className="eyebrow mb-3">YOUR WORKSPACE DEFAULTS</div><h2 className="panel-heading">{studio.studio_name}</h2><p className="text-xs text-secondary leading-6 mt-2">Catalog currency: <strong>{studio.currency}</strong><br />{studio.tax_label}: {studio.default_tax_percent}% · Contingency: {studio.default_contingency_percent}%</p><p className="field-help mt-3">Defaults are frozen into each new proposal. Settings changes preserve earlier versions.</p></div>
        {studio.synthetic && <div className="soft-card p-5"><div className="eyebrow mb-2">SYNTHETIC STARTER</div><p className="text-xs text-secondary leading-6 mb-3">Try a website brief with enough detail to see the complete review workflow.</p><button type="button" className="btn" disabled={readOnly || !!text || !!company || source === 'pdf'} onClick={() => { setCompany('Acme Fieldworks'); setText('We need a five-page website with analytics in twelve weeks. Our budget is $20,000. Final approved copy and photography are available. We also need a one-way contact form integration with our CRM.') }}>Load example brief <ArrowRight size={13} /></button><p className="field-help mt-2">Available when the brief is empty.</p></div>}
      </aside>
    </div>
  </div>
}
