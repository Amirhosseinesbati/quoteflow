import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, BookOpenText, ChevronRight, ClipboardCheck, FilePlus2, FolderOpen, LayoutGrid, LogOut, Sparkles } from 'lucide-react'
import { api } from './lib/api'
import type { Role, Session, Workspace } from './lib/types'
import { messageOf } from './lib/format'
import { Notice } from './components/Ui'
import { StudioPage } from './features/StudioPage'
import { BriefsPage } from './features/BriefsPage'
import { ApprovalsPage } from './features/ApprovalsPage'
import { CatalogPage } from './features/CatalogPage'
import { PortalPage } from './features/PortalPage'

type View = 'studio' | 'briefs' | 'approvals' | 'catalog'
interface Route { view: View; briefId?: string }

function readRoute(): Route {
  const params = new URLSearchParams(window.location.search)
  const view = params.get('view')
  return { view: view === 'briefs' || view === 'approvals' || view === 'catalog' ? view : 'studio', briefId: params.get('brief') || undefined }
}

const navItems = [
  { id: 'studio', label: 'Studio', icon: LayoutGrid },
  { id: 'briefs', label: 'Briefs', icon: FolderOpen },
  { id: 'approvals', label: 'Review queue', icon: ClipboardCheck },
  { id: 'catalog', label: 'Service catalog', icon: BookOpenText },
] as const

function Brand() {
  return <div className="brand"><span className="brand-mark"><Sparkles size={18} strokeWidth={1.8} /></span><span className="brand-word">Quote<span>Flow</span></span></div>
}

function Login({ onLogin, busy, error, connected }: { onLogin: (workspace: Workspace, role: Role) => void; busy: boolean; error: string; connected: boolean }) {
  const [workspace, setWorkspace] = useState<Workspace>('arc-field-demo')
  const [role, setRole] = useState<Role>('operator')
  return <div className="login-page">
    <div className="login-art">
      <div className="brand !p-0 !text-white"><span className="brand-mark"><Sparkles size={18} /></span><span className="brand-word">Quote<span>Flow</span></span></div>
      <h1 className="login-quote">The best projects start with a <em>clear proposal.</em></h1>
      <div className="relative z-10 text-[10px] tracking-[.15em] uppercase text-[#b8c2b6]">ARC & FIELD STUDIO · PROPOSAL WORKSPACE</div>
    </div>
    <div className="login-form-wrap"><div className="login-form">
      <div className="eyebrow">A considered way to quote</div>
      <h2 className="serif text-[38px] leading-[1.1] mt-3 mb-3">Welcome to the studio.</h2>
      <p className="text-[13px] leading-[1.7] text-[#757c73] mb-8">Shape a messy brief into a precise scope, a confident price, and a proposal your client can understand.</p>
      <div className="alert info mb-7"><span className="connection-dot mt-1.5" /> <span><strong>Synthetic demo dataset.</strong> All companies, people, prices, and messages in this workspace are fictional. Live notifications are never sent in demo mode.</span></div>
      <div className="field mb-5"><label htmlFor="workspace">WORKSPACE</label>
        <select id="workspace" className="select" value={workspace} onChange={(event) => setWorkspace(event.target.value as Workspace)}>
          <option value="arc-field-demo">Arc & Field Studio</option>
          <option value="arc-field-isolation">Isolation test workspace</option>
        </select>
      </div>
      <div className="field mb-7"><label>DEMO ROLE</label><div className="role-options" role="group" aria-label="Demo role">
        {(['admin','operator','viewer'] as const).map((choice) => <button type="button" key={choice} className={`role-option ${role === choice ? 'selected' : ''}`} aria-pressed={role === choice} onClick={() => setRole(choice)}>{choice}</button>)}
      </div><span className="field-help">Role boundaries are enforced by the API; choose a role to inspect each experience.</span></div>
      {error && <div className="mb-5"><Notice tone="error">{error}</Notice></div>}
      {!connected && <div className="mb-5"><Notice tone="error">The API is disconnected. Start the demo services, then try again.</Notice></div>}
      <button className="btn btn-primary w-full !min-h-[44px]" type="button" disabled={busy || !connected} onClick={() => onLogin(workspace, role)}>
        {busy ? 'Opening workspace…' : 'Enter demo workspace'} <ArrowRight size={15} />
      </button>
      <p className="mt-5 text-[10px] text-[#9b9f97] leading-[1.6]">Local demonstration only · Proposal acceptance is a workflow acknowledgement, not an electronic signature.</p>
    </div></div>
  </div>
}

export default function App() {
  const portalToken = window.location.pathname.startsWith('/portal/') ? decodeURIComponent(window.location.pathname.split('/')[2] || '') : ''
  const [route, setRoute] = useState<Route>(readRoute)
  const [session, setSession] = useState<Session | null>(null)
  const [authBusy, setAuthBusy] = useState(false)
  const [authError, setAuthError] = useState('')
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false, refetchInterval: 30_000 })
  const approvals = useQuery({ queryKey: ['approvals'], queryFn: api.listApprovals, enabled: !!session && session.role !== 'viewer' })

  useEffect(() => {
    if (portalToken) return
    const stored = sessionStorage.getItem('quoteflow-demo-preference')
    if (!stored) return
    try {
      const preference = JSON.parse(stored) as { workspace: Workspace; role: Role }
      setAuthBusy(true)
      api.demoLogin(preference.workspace, preference.role).then(setSession).catch(() => sessionStorage.removeItem('quoteflow-demo-preference')).finally(() => setAuthBusy(false))
    } catch { sessionStorage.removeItem('quoteflow-demo-preference') }
  }, [portalToken])

  useEffect(() => {
    const update = () => setRoute(readRoute())
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])

  function navigate(view: View, briefId?: string) {
    const url = new URL(window.location.href)
    url.searchParams.set('view', view)
    if (briefId) url.searchParams.set('brief', briefId)
    else url.searchParams.delete('brief')
    window.history.pushState(null, '', url)
    setRoute({ view, briefId })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function login(workspace: Workspace, role: Role) {
    setAuthBusy(true); setAuthError('')
    try {
      const result = await api.demoLogin(workspace, role)
      setSession(result)
      sessionStorage.setItem('quoteflow-demo-preference', JSON.stringify({ workspace, role }))
    } catch (error) { setAuthError(messageOf(error)) }
    finally { setAuthBusy(false) }
  }

  if (portalToken) return <PortalPage token={portalToken} />
  if (!session) return <Login onLogin={login} busy={authBusy} error={authError} connected={health.isSuccess && health.data.status === 'ok'} />

  const workspaceName = typeof session.workspace === 'string' ? session.workspace : session.workspace.name || session.workspace.id
  const queueCount = approvals.data?.filter((item) => item.status === 'pending').length || 0
  const title = route.view === 'studio' ? 'Proposal studio' : route.view === 'briefs' ? 'Briefs' : route.view === 'approvals' ? 'Review queue' : 'Service catalog'

  return <div className="app-shell">
    <aside className="sidebar" aria-label="Main navigation">
      <Brand />
      <div className="nav-label">Workspace</div>
      <nav aria-label="Primary">
        {navItems.map((item) => <button type="button" key={item.id} className={`nav-link ${route.view === item.id ? 'active' : ''}`} aria-current={route.view === item.id ? 'page' : undefined} onClick={() => navigate(item.id)} title={item.label}>
          <item.icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{item.id === 'approvals' && queueCount > 0 && <span className="nav-count">{queueCount}</span>}
        </button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="workspace-chip"><div className="workspace-avatar">A<span className="text-[#e0a28d]">&</span>F</div><div className="min-w-0"><div className="text-[11px] font-semibold truncate">Arc & Field Studio</div><div className="text-[9px] text-[#9ba097] capitalize">{session.role} · Demo</div></div></div>
        <div className="flex items-center gap-2 text-[10px] text-[#868d83] mt-3"><span className={`connection-dot ${health.isSuccess ? '' : 'off'}`} />{health.isSuccess ? `${health.data.mode || 'Demo'} API connected` : 'API disconnected'}</div>
        <p className="text-[9px] text-[#afb3aa] mt-5 leading-[1.4]">Synthetic demo dataset<br />{workspaceName}</p>
        <button type="button" onClick={() => { sessionStorage.removeItem('quoteflow-demo-preference'); setSession(null) }} className="btn btn-ghost btn-small mt-3 !px-0" title="Leave demo workspace"><LogOut size={12} /> Leave workspace</button>
      </div>
    </aside>
    <main className="main-area">
      <div className="topbar"><div className="topbar-title"><span>Workspace</span><ChevronRight size={12} /><strong>{title}</strong></div>
        <div className="topbar-right"><span className="badge coral">SYNTHETIC DEMO</span><span className="badge capitalize">{session.role}</span><button type="button" className="btn btn-small btn-primary" onClick={() => navigate('studio')}><FilePlus2 size={12} /> New brief</button></div>
      </div>
      {route.view === 'studio' && <StudioPage briefId={route.briefId} role={session.role} onBriefCreated={(id) => navigate('studio', id)} />}
      {route.view === 'briefs' && <BriefsPage onOpen={(id) => navigate('studio', id)} onNew={() => navigate('studio')} />}
      {route.view === 'approvals' && <ApprovalsPage role={session.role} onOpenBrief={(id) => navigate('studio', id)} />}
      {route.view === 'catalog' && <CatalogPage role={session.role} />}
    </main>
  </div>
}
