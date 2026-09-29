import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, FilePlus2, FolderOpen, Search } from 'lucide-react'
import { api } from '../lib/api'
import { messageOf, shortDate } from '../lib/format'
import { EmptyState, LoadingPanel, Notice, StatusBadge } from '../components/Ui'

export function BriefsPage({ onOpen, onNew }: { onOpen: (id: string) => void; onNew: () => void }) {
  const [search, setSearch] = useState('')
  const briefs = useQuery({ queryKey: ['briefs'], queryFn: api.listBriefs })
  const filtered = briefs.data?.filter((brief) => [brief.company_name, brief.contact_name, brief.text].some((value) => value?.toLowerCase().includes(search.toLowerCase()))) || []

  return <div className="page">
    <div className="page-header"><div><div className="eyebrow">Intake library</div><h1 className="page-title">Every project starts somewhere.</h1><p className="page-subtitle">Browse incoming briefs and pick up the conversation where it left off.</p></div>
      <button type="button" className="btn btn-primary" onClick={onNew}><FilePlus2 size={14} /> New brief</button>
    </div>
    <div className="panel">
      <div className="panel-header"><div><div className="panel-heading">Client briefs</div><p className="text-[11px] text-[#9a9f97] mt-1">{briefs.data?.length || 0} records in this workspace</p></div>
        <div className="relative w-[235px] max-w-full"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a4aaa1]" /><input aria-label="Search briefs" className="input !pl-9" placeholder="Search briefs…" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
      </div>
      {briefs.isPending ? <div className="p-5"><LoadingPanel label="Loading briefs…" /></div> : briefs.isError ? <div className="p-5"><Notice tone="error" onRetry={() => briefs.refetch()}>{messageOf(briefs.error)}</Notice></div> : filtered.length === 0 ?
        <EmptyState icon={<FolderOpen size={22} strokeWidth={1.5} />} title={search ? 'No matching briefs' : 'No briefs yet'} description={search ? 'Try a different company, contact, or phrase.' : 'Paste a client note into the studio to begin a proposal.'} action={!search && <button type="button" className="btn btn-coral" onClick={onNew}>Create a brief <ArrowRight size={13} /></button>} /> :
        <div className="table-wrap"><table className="data-table"><thead><tr><th>Client / brief</th><th>Contact</th><th>Created</th><th>Status</th><th></th></tr></thead><tbody>
          {filtered.map((brief) => <tr key={brief.id}>
            <td><button type="button" className="table-link text-left" onClick={() => onOpen(brief.id)}>{brief.company_name || 'Untitled client'}</button><div className="text-[#9aa097] max-w-[360px] truncate mt-1">{brief.text}</div></td>
            <td>{brief.contact_name || '—'}</td><td>{shortDate(brief.created_at)}</td><td><StatusBadge status={brief.status} /></td>
            <td><button type="button" className="icon-btn" aria-label={`Open brief for ${brief.company_name || 'untitled client'}`} onClick={() => onOpen(brief.id)}><ArrowRight size={14} /></button></td>
          </tr>)}
        </tbody></table></div>}
    </div>
  </div>
}
