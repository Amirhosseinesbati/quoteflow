import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownToLine, ArrowUpFromLine, Check, Settings2 } from 'lucide-react'
import { api } from '../lib/api'
import { messageOf, money } from '../lib/format'
import { defaultStudio, templateText } from '../lib/studio'
import type { Role, StudioProfile, StudioSettings } from '../lib/types'
import { LoadingPanel, Notice } from '../components/Ui'

function SettingsForm({ profile, role }: { profile: StudioProfile; role: Role }) {
  const client = useQueryClient()
  const [draft, setDraft] = useState(profile.settings)
  const [notice, setNotice] = useState('')
  const [importError, setImportError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const editable = role === 'admin'
  const dirty = JSON.stringify(draft) !== JSON.stringify(profile.settings)
  const save = useMutation({ mutationFn: () => api.saveStudioSettings(draft, profile.revision), onSuccess: (result) => {
    client.setQueryData(['studio-settings'], result)
    client.invalidateQueries({ queryKey: ['studio-settings'] })
  } })
  function update(key: keyof StudioSettings, value: string) { setDraft({ ...draft, [key]: value }); setNotice('') }
  function exportTemplate() {
    const url = URL.createObjectURL(new Blob([JSON.stringify({ schema_version: 1, settings: draft }, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = 'quoteflow-studio-template.json'; link.click(); URL.revokeObjectURL(url)
    setNotice('Studio template exported. It contains branding and defaults only; catalog services are managed separately.')
  }
  async function importTemplate(file?: File) {
    setImportError(''); setNotice('')
    if (!file) return
    try {
      if (file.size > 24_000) throw new Error('Choose a studio template smaller than 24 KB.')
      const data = JSON.parse(await file.text()) as { schema_version?: number; settings?: Record<string, unknown> }
      const keys = Object.keys(defaultStudio)
      if (data.schema_version !== 1 || !data.settings || Object.keys(data.settings).length !== keys.length || !keys.every((key) => typeof data.settings?.[key] === 'string')) throw new Error('This file is not a QuoteFlow studio template (schema version 1).')
      const imported = data.settings as unknown as StudioSettings
      if (!['USD','EUR','GBP','CAD','AUD','CHF'].includes(imported.currency) || !/^#[0-9a-f]{6}$/i.test(imported.accent_color)) throw new Error('The template currency or accent color is unsupported.')
      setDraft(imported); setNotice('Template loaded for review. Save studio settings to apply it to future options.')
    } catch (error) { setImportError(messageOf(error)) }
    finally { if (fileInput.current) fileInput.current.value = '' }
  }
  const textFields: Array<[keyof StudioSettings, string, number]> = [
    ['title_template', 'PROPOSAL TITLE', 2], ['summary_template', 'SUMMARY TEMPLATE', 4], ['terms', 'TERMS & START CONDITIONS', 5], ['footer_note', 'FOOTER NOTE', 2],
  ]
  return <>
    <div className="page-actions mb-5"><button className="btn" type="button" onClick={exportTemplate}><ArrowDownToLine size={14} /> Export template</button><button className="btn" type="button" disabled={!editable} onClick={() => fileInput.current?.click()}><ArrowUpFromLine size={14} /> Import template</button><input ref={fileInput} type="file" accept=".json,application/json" className="hidden" aria-label="Import studio template" onChange={(event) => void importTemplate(event.target.files?.[0])} /><span className="text-xs muted">Revision {profile.revision} · {dirty ? 'Unsaved changes' : 'Saved defaults'}</span></div>
    {notice && <div className="mb-4"><Notice>{notice}</Notice></div>}
    {importError && <div className="mb-4"><Notice tone="error">{importError}</Notice></div>}
    {save.isError && <div className="mb-4"><Notice tone="error">{messageOf(save.error)}</Notice></div>}
    {!editable && <div className="mb-4"><Notice>Settings are read only for {role} users. An admin can save brand, pricing, and template defaults.</Notice></div>}
    <div className="settings-grid">
      <form className="panel" onSubmit={(event) => { event.preventDefault(); save.mutate() }}>
        <div className="panel-header"><h2 className="panel-heading">Make it your studio</h2><Settings2 size={18} /></div>
        <div className="panel-body"><fieldset disabled={!editable || save.isPending}>
          <legend className="eyebrow mb-4">Brand & investment</legend>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="field"><label htmlFor="studio-name">STUDIO NAME</label><input id="studio-name" className="input" required minLength={2} maxLength={100} value={draft.studio_name} onChange={(event) => update('studio_name', event.target.value)} /></div>
            <div className="field"><label htmlFor="accent-color">DOCUMENT ACCENT</label><div className="flex gap-2 items-center"><input id="accent-color" type="color" className="color-input" value={draft.accent_color} onChange={(event) => update('accent_color', event.target.value)} /><span className="text-xs muted">{draft.accent_color}</span></div></div>
            <div className="field"><label htmlFor="studio-currency">CATALOG CURRENCY</label><select id="studio-currency" className="select" value={draft.currency} onChange={(event) => update('currency', event.target.value)}>{['USD','EUR','GBP','CAD','AUD','CHF'].map((currency) => <option key={currency}>{currency}</option>)}</select></div>
            <div className="field"><label htmlFor="tax-label">TAX LABEL</label><input id="tax-label" className="input" required maxLength={24} value={draft.tax_label} onChange={(event) => update('tax_label', event.target.value)} /></div>
            {([['default_tax_percent','DEFAULT TAX %'],['default_contingency_percent','DEFAULT CONTINGENCY %'],['approval_discount_threshold','REVIEW DISCOUNTS ABOVE %']] as const).map(([key,label]) => <div className="field" key={key}><label htmlFor={key}>{label}</label><input id={key} type="number" min="0" max="100" step="0.01" required className="input" value={draft[key]} onChange={(event) => update(key, event.target.value)} /></div>)}
          </div>
          <p className="field-help mt-4">Currency labels catalog rates; no exchange conversion is performed. Review rates before generating new options. Totals use two decimal places.</p>
          <div className="section-rule my-6" /><div className="eyebrow mb-3">Your proposal language</div><p className="field-help mb-4">Use {'{studio}'}, {'{client}'}, and {'{package}'} in the title or summary. Terms are editable in each proposal.</p>
          <div className="grid gap-4">{textFields.map(([key,label,rows]) => <div className="field" key={key}><label htmlFor={key}>{label}</label><textarea id={key} className="textarea" rows={rows} required={key !== 'footer_note'} maxLength={key === 'terms' ? 4000 : key === 'summary_template' ? 1500 : 160} value={draft[key]} onChange={(event) => update(key, event.target.value)} /></div>)}</div>
        </fieldset>
        <div className="flex flex-wrap gap-3 items-center mt-6"><button type="submit" className="btn btn-primary" disabled={!editable || !dirty || save.isPending}><Check size={14} /> {save.isPending ? 'Saving…' : 'Save studio settings'}</button><button type="button" className="btn" disabled={!dirty || save.isPending} onClick={() => { setDraft(profile.settings); setNotice('Changes discarded.') }}>Discard changes</button></div>
        </div>
      </form>
      <aside className="settings-preview"><div className="proposal-paper !min-h-0" style={{ borderTop: `4px solid ${draft.accent_color}` }}><div className="eyebrow">Template preview / Example client</div><div className="paper-logo mt-5">{draft.studio_name}</div><h2 className="paper-title !text-[34px]">{templateText(draft.title_template, draft.studio_name, 'Example client', 'recommended')}</h2><p className="paper-intro">{templateText(draft.summary_template, draft.studio_name, 'Example client', 'recommended')}</p><div className="paper-section mt-6"><h3>Investment</h3><p>{money(2500, draft.currency)} <span className="block mt-2">{draft.tax_label}: {draft.default_tax_percent}% · Contingency: {draft.default_contingency_percent}%</span></p></div><div className="paper-section"><h3>Terms</h3><p>{draft.terms}</p></div><div className="paper-footer">{draft.footer_note}</div></div><div className="soft-card p-5 mt-4"><h3 className="serif text-xl">Built to travel.</h3><p className="text-xs muted leading-7 mt-2">Export your studio defaults to reuse in another installation. New options freeze these settings with their catalog and content hash. Existing proposals keep their original identity.</p></div></aside>
    </div>
  </>
}

export function SettingsPage({ role }: { role: Role }) {
  const profile = useQuery({ queryKey: ['studio-settings'], queryFn: api.studioSettings })
  return <div className="page"><div className="page-header"><div><div className="eyebrow">A workspace of your own</div><h1 className="page-title">Your studio, your standards.</h1><p className="page-subtitle">Set the brand, commercial defaults, and proposal language for your next client.</p></div></div>{profile.isPending ? <LoadingPanel label="Loading studio settings…" /> : profile.isError ? <Notice tone="error" onRetry={() => profile.refetch()}>{messageOf(profile.error)}</Notice> : <SettingsForm key={profile.data.revision} profile={profile.data} role={role} />}</div>
}
