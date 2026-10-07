import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, BookOpenText, ChevronRight, ClipboardCheck, FilePlus2, FolderOpen, Layers3, LayoutGrid, LogOut, Settings2, Sparkles } from 'lucide-react'
import { api } from './lib/api'
import type { Role, Session, Workspace } from './lib/types'
import { messageOf } from './lib/format'
import { Notice } from './components/Ui'
import { StudioPage } from './features/StudioPage'
import { BriefsPage } from './features/BriefsPage'
import { ApprovalsPage } from './features/ApprovalsPage'
import { CatalogPage } from './features/CatalogPage'
import { PortalPage } from './features/PortalPage'
import { SettingsPage } from './features/SettingsPage'
import { defaultStudio, StudioContext } from './lib/studio'
import { ThemeControl } from './lib/theme'

type View = 'studio' | 'briefs' | 'approvals' | 'catalog' | 'settings'
interface Route { view: View; briefId?: string }

function readRoute(): Route {
  const params = new URLSearchParams(window.location.search)
  const view = params.get('view')
  return { view: view === 'briefs' || view === 'approvals' || view === 'catalog' || view === 'settings' ? view : 'studio', briefId: params.get('brief') || undefined }
}

const navItems = [
  { id: 'studio', label: 'Studio', icon: LayoutGrid },
  { id: 'briefs', label: 'Briefs', icon: FolderOpen },
  { id: 'approvals', label: 'Review queue', icon: ClipboardCheck },
  { id: 'catalog', label: 'Service catalog', icon: BookOpenText },
  { id: 'settings', label: 'Studio settings', icon: Settings2 },
] as const

function Brand() {
  return <div className="brand"><span className="brand-mark"><Layers3 size={18} strokeWidth={1.8} /></span><span className="brand-word">Quote<span>Flow</span><small>PROPOSAL WORKBENCH</small></span></div>
}

function Login({ onLogin, busy, error, connected }: { onLogin: (workspace: Workspace, role: Role) => void; busy: boolean; error: string; connected: boolean }) {
  const [workspace, setWorkspace] = useState<Workspace>('arc-field-demo')
  const [role, setRole] = useState<Role>('operator')
  return <div className="login-page">
    <div className="login-art"><Brand />
      <div className="login-blueprint"><div className="eyebrow">FROM SIGNAL TO SCOPE</div><h1 className="login-quote">A clear scope.<br /><em>A confident next step.</em></h1><p>One workbench for the brief, the numbers, and the version your client approves.</p><ol className="blueprint-stages">{[['01', 'Capture the brief', 'Source words → traceable requirements'], ['02', 'Resolve the unknowns', 'Focused questions → explicit assumptions'], ['03', 'Compare three directions', 'Catalog services → deterministic pricing'], ['04', 'Approve the exact version', 'Review → PDF → project handoff']].map(([number, title, detail]) => <li key={number}><span>{number}</span><div><strong>{title}</strong><small>{detail}</small></div></li>)}</ol></div>
      <div className="login-footnote"><span className="connection-dot" /> LOCAL DEMO / NO LIVE DELIVERY</div>
    </div>
    <div className="login-form-wrap"><div className="login-form">
      <div className="login-form-top"><div className="eyebrow">WORKSPACE ACCESS</div><ThemeControl /></div>
      <h2 className="login-heading">Open your workbench.</h2>
      <p className="text-sm text-secondary leading-6 mb-6">Trace the brief. Compare three scopes. Share a version your client can understand.</p>
      <div className="alert info mb-6"><Sparkles size={15} className="shrink-0 mt-1" /><span><strong>Synthetic demo dataset.</strong> Companies, people and prices are fictional. No live notifications are sent.</span></div>
      <div className="field mb-5"><label htmlFor="workspace">WORKSPACE</label><select id="workspace" className="select" value={workspace} onChange={(event) => setWorkspace(event.target.value as Workspace)}><option value="arc-field-demo">Arc & Field Studio</option><option value="arc-field-isolation">Isolation test workspace</option></select></div>
      <div className="field mb-6"><label>DEMO ROLE</label><div className="role-options" role="group" aria-label="Demo role">{(['admin','operator','viewer'] as const).map((choice) => <button type="button" key={choice} className={`role-option ${role === choice ? 'selected' : ''}`} aria-pressed={role === choice} onClick={() => setRole(choice)}>{choice}</button>)}</div><span className="field-help">API-enforced role boundaries. Choose a role to inspect its access.</span></div>
      {error && <div className="mb-5"><Notice tone="error">{error}</Notice></div>}
      {!connected && <div className="mb-5"><Notice tone="error">The API is disconnected. Start the demo services, then try again.</Notice></div>}
      <button className="btn btn-primary w-full" type="button" disabled={busy || !connected} onClick={() => onLogin(workspace, role)}>{busy ? 'Opening workspace.' : 'Enter demo workspace'} <ArrowRight size={15} /></button>
      <p className="mt-5 text-xs text-secondary leading-6">Local demonstration only. Acceptance is a workflow acknowledgement, not an electronic signature.</p>
    </div></div>
  </div>
}

export default function App() {
  const queryClient = useQueryClient()
  const portalToken = window.location.pathname.startsWith('/portal/') ? decodeURIComponent(window.location.pathname.split('/')[2] || '') : ''
  const [route, setRoute] = useState<Route>(readRoute)
  const [session, setSession] = useState<Session | null>(null)
  const [authBusy, setAuthBusy] = useState(true)
  const [authError, setAuthError] = useState('')
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false, refetchInterval: 30_000 })
  const approvals = useQuery({ queryKey: ['approvals'], queryFn: api.listApprovals, enabled: !!session && session.role !== 'viewer' })
  const profile = useQuery({ queryKey: ['studio-settings'], queryFn: api.studioSettings, enabled: !!session })

  useEffect(() => {
    if (portalToken) return
    try { sessionStorage.removeItem('quoteflow-demo-preference') } catch { /* A session does not require browser storage. */ }
    api.me().then(setSession).catch(() => setSession(null)).finally(() => setAuthBusy(false))
  }, [portalToken])

  useEffect(() => {
    const expired = () => { setSession(null); queryClient.clear(); setAuthError('Your session has expired. Sign in again to continue.') }
    window.addEventListener('quoteflow-session-expired', expired)
    return () => window.removeEventListener('quoteflow-session-expired', expired)
  }, [queryClient])

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
    window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
  }

  async function login(workspace: Workspace, role: Role) {
    setAuthBusy(true); setAuthError('')
    try {
      const result = await api.demoLogin(workspace, role)
      setSession(result)
    } catch (error) { setAuthError(messageOf(error)) }
    finally { setAuthBusy(false) }
  }

  if (portalToken) return <PortalPage token={portalToken} />
  if (!session && health.data?.synthetic === false) return <ConnectedLogin busy={authBusy} error={authError} onLogin={async (email, password) => { setAuthBusy(true); setAuthError(''); try { setSession(await api.login(email, password)) } catch (error) { setAuthError(messageOf(error)) } finally { setAuthBusy(false) } }} />
  if (!session) return <Login onLogin={login} busy={authBusy} error={authError} connected={health.isSuccess && health.data.status === 'ok'} />

  const workspaceName = typeof session.workspace === 'string' ? session.workspace : session.workspace.name || session.workspace.id
  const queueCount = approvals.data?.filter((item) => item.status === 'pending').length || 0
  const title = route.view === 'studio' ? 'Proposal studio' : route.view === 'briefs' ? 'Briefs' : route.view === 'approvals' ? 'Review queue' : route.view === 'settings' ? 'Studio settings' : 'Service catalog'
  const studio = profile.data?.settings || defaultStudio
  const synthetic = health.data?.synthetic !== false

  async function logout() {
    setAuthBusy(true)
    try { await api.logout(); setSession(null); queryClient.clear(); setAuthError('') }
    catch (error) { setAuthError(messageOf(error)) }
    finally { setAuthBusy(false) }
  }

  return <StudioContext.Provider value={{ ...studio, synthetic }}><div className="app-shell"><a className="skip-link" href="#workspace-content">Skip to workspace</a>
    <aside className="sidebar" aria-label="Main navigation">
      <Brand />
      <div className="nav-label">Workspace</div>
      <nav aria-label="Primary">
        {navItems.map((item) => <button type="button" key={item.id} className={`nav-link ${route.view === item.id ? 'active' : ''}`} aria-current={route.view === item.id ? 'page' : undefined} onClick={() => navigate(item.id)} title={item.label} aria-label={item.label}>
          <item.icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{item.id === 'approvals' && queueCount > 0 && <span className="nav-count">{queueCount}</span>}
        </button>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="workspace-chip"><div className="workspace-avatar">{studio.studio_name.slice(0, 2).toUpperCase()}</div><div className="min-w-0"><div className="text-[11px] font-semibold truncate">{studio.studio_name}</div><div className="text-[9px] text-secondary capitalize">{session.role} · {synthetic ? 'Demo' : 'Connected'}</div></div></div>
        <div className="flex items-center gap-2 text-[10px] text-secondary mt-3"><span className={`connection-dot ${health.isSuccess ? '' : 'off'}`} />{health.isSuccess ? `${health.data.mode || 'Demo'} API connected` : 'API disconnected'}</div>
        <p className="text-[9px] text-secondary mt-5 leading-[1.4]">{synthetic ? 'Synthetic demo dataset' : 'Connected workspace'}<br />{workspaceName}</p>
        <button type="button" disabled={authBusy} onClick={() => void logout()} className="btn btn-ghost btn-small mt-3 !px-0" title="Sign out of workspace"><LogOut size={12} /> Leave workspace</button>
      </div>
    </aside>
    <main className="main-area" id="workspace-content" tabIndex={-1}>
      <div className="topbar"><div className="topbar-title"><span>Workspace</span><ChevronRight size={12} /><strong>{title}</strong></div>
        <div className="topbar-right"><span className="badge coral mode-badge">{synthetic ? 'SYNTHETIC DEMO' : 'CONNECTED'}</span><span className="badge capitalize role-badge">{session.role}</span><ThemeControl /><button type="button" disabled={session.role === 'viewer'} className="btn btn-small btn-primary new-brief" onClick={() => navigate('studio')}><FilePlus2 size={12} /> <span>New brief</span></button><button type="button" className="icon-btn mobile-logout" aria-label="Sign out" disabled={authBusy} onClick={() => void logout()}><LogOut size={14} /></button></div>
      </div>
      {authError && <div className="page !pb-0"><Notice tone="error">{authError}</Notice></div>}
      {profile.isError && <div className="page !pb-0"><Notice tone="error" onRetry={() => profile.refetch()}>{messageOf(profile.error)}</Notice></div>}
      {route.view === 'studio' && <StudioPage briefId={route.briefId} role={session.role} onBriefCreated={(id) => navigate('studio', id)} />}
      {route.view === 'briefs' && <BriefsPage onOpen={(id) => navigate('studio', id)} onNew={() => navigate('studio')} />}
      {route.view === 'approvals' && <ApprovalsPage role={session.role} onOpenBrief={(id) => navigate('studio', id)} />}
      {route.view === 'catalog' && <CatalogPage role={session.role} />}
      {route.view === 'settings' && <SettingsPage role={session.role} />}
    </main>
  </div></StudioContext.Provider>
}

function ConnectedLogin({ busy, error, onLogin }: { busy: boolean; error: string; onLogin: (email: string, password: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  return <div className="login-form-wrap min-h-screen"><form className="login-form" onSubmit={(event) => { event.preventDefault(); onLogin(email, password) }}><div className="login-form-top"><Brand /><ThemeControl /></div><h1 className="page-title">Sign in to your studio.</h1><p className="page-subtitle mb-6">Connected workspace. Use an account provisioned by your administrator.</p><div className="field mb-4"><label htmlFor="login-email">EMAIL</label><input id="login-email" type="email" className="input" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} /></div><div className="field mb-5"><label htmlFor="login-password">PASSWORD</label><input id="login-password" type="password" className="input" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></div>{error && <Notice tone="error">{error}</Notice>}<button className="btn btn-primary mt-4 w-full" disabled={busy} type="submit">{busy ? 'Signing in…' : 'Sign in'}</button></form></div>
}
