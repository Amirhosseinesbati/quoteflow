import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowRight, FileText, Mail, Paperclip, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { messageOf } from '../lib/format'
import { Notice } from '../components/Ui'

export function IntakeForm({ onCreated }: { onCreated: (id: string) => void }) {
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
  const valid = source === 'pdf' ? !!file && file.size <= 5_000_000 && file.type === 'application/pdf' : text.trim().length >= 20

  return <div className="page">
    <div className="page-header"><div><div className="eyebrow">From first conversation to clear commitment</div><h1 className="page-title">Turn a brief into a better beginning.</h1><p className="page-subtitle max-w-[590px]">Bring in the messy details. QuoteFlow extracts what matters, asks what is missing, and keeps the final price grounded in your catalog.</p></div><span className="badge coral">SYNTHETIC DEMO DATA</span></div>
    <div className="studio-grid">
      <section className="panel"><div className="panel-header"><div className="flex items-center gap-2"><span className="text-coral"><FileText size={17} /></span><h2 className="panel-heading">Start with a client brief</h2></div><span className="eyebrow">01 / INTAKE</span></div>
        <form className="panel-body" onSubmit={(event) => { event.preventDefault(); if (valid) create.mutate() }}>
          <div className="flex gap-2 mb-5 flex-wrap" role="group" aria-label="Brief source"><button type="button" className={`btn ${source === 'paste' ? 'btn-primary' : ''}`} aria-pressed={source === 'paste'} onClick={() => setSource('paste')}><Mail size={13} /> Pasted email</button><button type="button" className={`btn ${source === 'form' ? 'btn-primary' : ''}`} aria-pressed={source === 'form'} onClick={() => setSource('form')}><FileText size={13} /> Demo form</button><button type="button" className={`btn ${source === 'pdf' ? 'btn-primary' : ''}`} aria-pressed={source === 'pdf'} onClick={() => setSource('pdf')}><Paperclip size={13} /> PDF brief</button></div>
          {source === 'pdf' ? <div className="field mb-5"><label htmlFor="brief-file">PDF ATTACHMENT *</label><input id="brief-file" type="file" accept="application/pdf,.pdf" className="input !py-4" onChange={(event) => setFile(event.target.files?.[0] || null)} /><span className="field-help">PDF only, maximum 5 MB. The file is validated by the API; extracted text becomes the source brief.</span>{file && file.size > 5_000_000 && <span className="text-[10px] text-[#b2574a]">This file is larger than 5 MB.</span>}</div> : <>
            <div className="field mb-5"><label htmlFor="brief-text">CLIENT NOTE OR PROJECT BRIEF *</label><textarea id="brief-text" className="textarea min-h-[250px]" value={text} onChange={(event) => setText(event.target.value)} placeholder={'Hi, we are refreshing our brand and need a new website by October. We have some photography, but no content yet. Could you include a few options? Our rough budget is…'} required minLength={20} /><span className="field-help">Include the original wording. Evidence is kept alongside every extracted requirement.</span></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4"><div className="field"><label htmlFor="company">COMPANY (OPTIONAL)</label><input id="company" className="input" value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Client company" /></div><div className="field"><label htmlFor="contact">CONTACT NAME (OPTIONAL)</label><input id="contact" className="input" value={contact} onChange={(event) => setContact(event.target.value)} placeholder="Client contact" /></div></div>
            <div className="field mb-5"><label htmlFor="email">CONTACT EMAIL (OPTIONAL)</label><input id="email" className="input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" /><span className="field-help">Demo mode records notifications locally; no email is sent.</span></div>
          </>}
          {create.isError && <div className="mb-4"><Notice tone="error">{messageOf(create.error)}</Notice></div>}
          <div className="flex items-center justify-between gap-3 flex-wrap border-t border-[#efede7] pt-5"><span className="text-[10px] text-[#9aa097]">{source === 'pdf' ? 'PDF · 5 MB maximum' : '20 character minimum'} · Review before pricing</span><button type="submit" className="btn btn-coral !min-h-[39px]" disabled={!valid || create.isPending}>{create.isPending ? 'Saving brief…' : 'Create brief'} <ArrowRight size={14} /></button></div>
        </form>
      </section>
      <div className="studio-right">
        <div className="panel overflow-hidden"><div className="panel-header"><div className="flex items-center gap-2"><Sparkles size={16} className="text-coral" /><div className="panel-heading">A proposal in motion</div></div><span className="eyebrow">PREVIEW</span></div>
          <div className="p-5"><div className="proposal-paper !min-h-[560px] opacity-90"><div className="paper-meta"><div className="paper-logo">ARC <span>&</span> FIELD<br /><span className="text-[9px] tracking-[.2em] font-sans font-semibold text-[#8a8f87]">STUDIO</span></div><div className="text-right text-[9px] tracking-[.15em] text-[#a9afa6]">PROPOSAL / DRAFT</div></div>
            <div className="eyebrow mt-10">Prepared for your next project</div><h2 className="paper-title">Clarity makes<br />space for craft.</h2><p className="paper-intro">A strong proposal starts by understanding the work, the constraints, and the open questions. Your document will take shape here as you move through the studio.</p>
            <div className="mt-12 space-y-5"><div className="paper-section"><h3>01 / Discovery</h3><p>Capture the brief and trace each requirement to the client’s words.</p></div><div className="paper-section"><h3>02 / Scope</h3><p>Compare three distinct directions based on a versioned service catalog.</p></div><div className="paper-section"><h3>03 / Proposal</h3><p>Review clear deliverables, assumptions, exclusions, and a deterministic total.</p></div></div>
          </div></div>
        </div>
        <div className="soft-card p-5"><div className="eyebrow mb-2">The studio method</div><p className="serif text-[19px] leading-[1.35]">Every scope decision leaves a trace. Every number has a rule.</p><p className="text-[11px] text-[#878d84] mt-2 leading-[1.6]">Demo responses are simulated through the same product workflow. The final commercial and legal terms should be configured for each customer.</p></div>
      </div>
    </div>
  </div>
}
