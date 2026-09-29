import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpenText, Plus, Search, X } from 'lucide-react'
import { api } from '../lib/api'
import { messageOf, money } from '../lib/format'
import type { CatalogService, Role } from '../lib/types'
import { EmptyState, LoadingPanel, Notice, StatusBadge } from '../components/Ui'

type ServiceInput = Omit<CatalogService, 'id'>
const blank: ServiceInput = { code: '', name: '', category: 'Website design', description: '', unit: 'project', base_price: '0.00', active: true }
const categories = ['Branding', 'Website design', 'Integrations', 'Maintenance']

export function CatalogPage({ role }: { role: Role }) {
  const client = useQueryClient()
  const catalog = useQuery({ queryKey: ['catalog'], queryFn: api.getCatalog })
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All services')
  const [editing, setEditing] = useState<CatalogService | 'new' | null>(null)
  const [form, setForm] = useState<ServiceInput>(blank)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const save = useMutation({
    mutationFn: () => editing === 'new' ? api.createService(form) : api.updateService((editing as CatalogService).id, form),
    onSuccess: () => { setEditing(null); setSuccess('Catalog version updated. New quotes will use the latest service rules.'); client.invalidateQueries({ queryKey: ['catalog'] }) },
    onError: (cause) => setError(messageOf(cause)),
  })
  useEffect(() => { if (editing === 'new') setForm(blank); else if (editing) { const { id: _id, ...service } = editing; void _id; setForm(service) } setError('') }, [editing])
  const filtered = useMemo(() => catalog.data?.services.filter((item) => (category === 'All services' || item.category === category) && [item.name,item.code,item.description].some((value) => value.toLowerCase().includes(search.toLowerCase()))) || [], [catalog.data, category, search])
  const activeCount = catalog.data?.services.filter((item) => item.active).length || 0

  return <div className="page">
    <div className="page-header"><div><div className="eyebrow">The source of truth</div><h1 className="page-title">Price with purpose.</h1><p className="page-subtitle">Services and rates are versioned. The proposal model describes scope; the pricing engine computes totals.</p></div>
      <button type="button" className="btn btn-primary" disabled={role !== 'admin'} title={role !== 'admin' ? 'Admin access required' : undefined} onClick={() => setEditing('new')}><Plus size={14} /> Add service</button>
    </div>
    {success && <div className="mb-5"><Notice tone="success">{success}</Notice></div>}
    {role !== 'admin' && <div className="mb-5"><Notice tone="info">The catalog is read only for {role} users. An admin can change service rules.</Notice></div>}
    {catalog.isPending ? <LoadingPanel label="Loading catalog…" /> : catalog.isError ? <Notice tone="error" onRetry={() => catalog.refetch()}>{messageOf(catalog.error)}</Notice> : <>
      <div className="flex flex-wrap gap-3 mb-5"><div className="soft-card px-4 py-3"><span className="eyebrow">Current version</span><div className="serif text-[21px] mt-1">{catalog.data.version}</div></div><div className="soft-card px-4 py-3"><span className="eyebrow">Active services</span><div className="serif text-[21px] mt-1">{activeCount} / {catalog.data.services.length}</div></div><div className="soft-card px-4 py-3"><span className="eyebrow">Categories</span><div className="serif text-[21px] mt-1">{new Set(catalog.data.services.map((item) => item.category)).size}</div></div></div>
      <div className="panel"><div className="panel-header flex-wrap"><div><div className="panel-heading">Service library</div><p className="text-[11px] text-[#999f96] mt-1">Fictional rates for the Arc & Field demonstration.</p></div>
        <div className="flex flex-wrap gap-2"><div className="relative"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a4aaa1]" /><input aria-label="Search services" className="input !pl-9 !w-[190px]" placeholder="Search services…" value={search} onChange={(event) => setSearch(event.target.value)} /></div><select aria-label="Filter category" className="select !w-auto" value={category} onChange={(event) => setCategory(event.target.value)}><option>All services</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></div>
      </div>
      {filtered.length === 0 ? <EmptyState icon={<BookOpenText size={22} />} title="No services found" description="Change the search or category filter to see other catalog entries." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Service</th><th>Category</th><th>Unit</th><th>Base price</th><th>Status</th><th></th></tr></thead><tbody>
        {filtered.map((service) => <tr key={service.id}><td><div className="font-semibold text-[#303830]">{service.name}</div><div className="text-[10px] text-[#92998f] mt-1">{service.code} · {service.description}</div></td><td>{service.category}</td><td>{service.unit}</td><td className="font-semibold text-[#313a31]">{money(service.base_price)}</td><td><StatusBadge status={service.active ? 'active' : 'inactive'} /></td><td><button type="button" className="btn btn-small" disabled={role !== 'admin'} onClick={() => setEditing(service)}>Edit</button></td></tr>)}
      </tbody></table></div>}</div>
    </>}
    {editing && <div className="fixed inset-0 z-50 bg-[#1f2722]/50 p-4 flex items-center justify-center" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditing(null) }}>
      <div className="panel w-full max-w-[560px] max-h-[90vh] overflow-y-auto shadow-xl" role="dialog" aria-modal="true" aria-labelledby="catalog-title"><div className="panel-header"><div><div className="eyebrow">Versioned catalog</div><h2 id="catalog-title" className="serif text-[25px] mt-1">{editing === 'new' ? 'Add a service' : 'Edit service'}</h2></div><button type="button" className="icon-btn" aria-label="Close editor" onClick={() => setEditing(null)}><X size={15} /></button></div>
        <form className="panel-body" onSubmit={(event) => { event.preventDefault(); setError(''); save.mutate() }}>
          <div className="grid grid-cols-2 gap-3 mb-4"><div className="field"><label htmlFor="service-code">SERVICE CODE</label><input id="service-code" className="input" value={form.code} required onChange={(event) => setForm({ ...form, code: event.target.value })} /></div><div className="field"><label htmlFor="service-category">CATEGORY</label><select id="service-category" className="select" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>{categories.map((item) => <option key={item}>{item}</option>)}</select></div></div>
          <div className="field mb-4"><label htmlFor="service-name">SERVICE NAME</label><input id="service-name" className="input" value={form.name} required onChange={(event) => setForm({ ...form, name: event.target.value })} /></div>
          <div className="field mb-4"><label htmlFor="service-description">DESCRIPTION</label><textarea id="service-description" className="textarea" rows={3} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></div>
          <div className="grid grid-cols-2 gap-3 mb-4"><div className="field"><label htmlFor="service-unit">UNIT</label><input id="service-unit" className="input" value={form.unit} required onChange={(event) => setForm({ ...form, unit: event.target.value })} /></div><div className="field"><label htmlFor="service-price">BASE PRICE (USD)</label><input id="service-price" className="input" type="number" min="0" step="0.01" value={form.base_price} required onChange={(event) => setForm({ ...form, base_price: event.target.value })} /></div></div>
          <label className="flex items-center gap-2 text-[11px] text-[#596258]"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /> Active in new quotes</label>
          {error && <div className="mt-4"><Notice tone="error">{error}</Notice></div>}
          <div className="flex justify-end gap-2 mt-6"><button type="button" className="btn" onClick={() => setEditing(null)}>Cancel</button><button type="submit" className="btn btn-primary" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save catalog version'}</button></div>
        </form>
      </div></div>}
  </div>
}
