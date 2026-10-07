import type {
  Approval, Brief, Catalog, CatalogService, Clarification, Health, PortalData,
  PricePreview, Proposal, PublishResult, Quote, QuoteDiff, QuoteLineEdit, QuoteVersion,
  Role, Session, Workspace, StudioProfile, StudioSettings,
} from './types'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  })
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('quoteflow-session-expired'))
    let message = `Request failed (${response.status})`
    try {
      const error = await response.json() as { detail?: string | Array<{ msg?: string }> }
      if (typeof error.detail === 'string') message = error.detail
      else if (Array.isArray(error.detail)) message = error.detail.map((item) => item.msg).filter(Boolean).join('; ') || message
    } catch { /* The server may return a non-JSON proxy error. */ }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

const json = (value: unknown) => JSON.stringify(value)
const segment = (value: string) => encodeURIComponent(value)

export const api = {
  health: () => request<Health>('/health'),
  me: () => request<Session>('/auth/me'),
  logout: () => request<{ status: string }>('/auth/logout', { method: 'POST' }),
  login: (email: string, password: string) => request<Session>('/auth/login', { method: 'POST', body: json({ email, password }) }),
  studioSettings: () => request<StudioProfile>('/studio-settings'),
  saveStudioSettings: (settings: StudioSettings, expected_revision: number) => request<StudioProfile>('/studio-settings', { method: 'PUT', body: json({ settings, expected_revision }) }),
  demoLogin: (workspace: Workspace, role: Role) => request<Session>('/auth/demo', {
    method: 'POST', body: json({ workspace, role }),
  }),
  listBriefs: async () => (await request<{ items: Brief[] }>('/briefs')).items,
  createBrief: (body: { source_type: 'paste' | 'form'; text: string; company_name?: string; contact_name?: string; contact_email?: string }) =>
    request<Brief>('/briefs', { method: 'POST', body: json(body) }),
  uploadBrief: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<Brief>('/briefs/upload', { method: 'POST', body })
  },
  getBrief: (id: string) => request<Brief>(`/briefs/${segment(id)}`),
  analyzeBrief: (id: string) => request<Brief>(`/briefs/${segment(id)}/analyze`, { method: 'POST' }),
  addClarification: (briefId: string, question: string) => request<Clarification>(`/briefs/${segment(briefId)}/clarifications`, {
    method: 'POST', body: json({ question }),
  }),
  answerClarification: (briefId: string, clarificationId: string, answer: string) =>
    request<Clarification>(`/briefs/${segment(briefId)}/clarifications/${segment(clarificationId)}/answer`, {
      method: 'POST', body: json({ answer }),
    }),
  briefPortalLink: (id: string) => request<{ token: string; portal_url: string }>(`/briefs/${segment(id)}/portal-link`, { method: 'POST' }),
  generateOptions: (id: string) => request<{ quote_id: string; options: QuoteVersion[] }>(`/briefs/${segment(id)}/options`, { method: 'POST' }),
  getQuote: (id: string) => request<Quote>(`/quotes/${segment(id)}`),
  updateVersion: (quoteId: string, versionId: string, body: {
    proposal?: Proposal; lines?: QuoteLineEdit[]; discount_percent?: string; tax_percent?: string; contingency_percent?: string
  }) => request<QuoteVersion>(`/quotes/${segment(quoteId)}/versions/${segment(versionId)}`, {
    method: 'PATCH', body: json(body),
  }),
  pricePreview: (quoteId: string, versionId: string, body: { lines?: QuoteLineEdit[]; discount_percent?: string; tax_percent?: string; contingency_percent?: string }) =>
    request<PricePreview>(`/quotes/${segment(quoteId)}/versions/${segment(versionId)}/price-preview`, {
      method: 'POST', body: json(body),
    }),
  submitReview: (quoteId: string, versionId: string) => request<Approval>(`/quotes/${segment(quoteId)}/versions/${segment(versionId)}/submit-review`, { method: 'POST' }),
  listApprovals: async () => (await request<{ items: Approval[] }>('/approvals')).items,
  decideApproval: (id: string, decision: 'approved' | 'rejected', note?: string) => request<Approval>(`/approvals/${segment(id)}/decision`, {
    method: 'POST', body: json({ decision, note }),
  }),
  publishVersion: (quoteId: string, versionId: string) => request<PublishResult>(`/quotes/${segment(quoteId)}/versions/${segment(versionId)}/publish`, { method: 'POST' }),
  pdfUrl: (quoteId: string, versionId: string) => `${baseUrl}/quotes/${segment(quoteId)}/versions/${segment(versionId)}/pdf`,
  quoteDiff: (quoteId: string, from: string, to: string) => request<QuoteDiff>(`/quotes/${segment(quoteId)}/diff?from=${segment(from)}&to=${segment(to)}`),
  getCatalog: (versionId?: string) => request<Catalog>(`/catalog${versionId ? `?version_id=${segment(versionId)}` : ''}`),
  createService: (body: Omit<CatalogService, 'id'>) => request<Catalog>('/catalog/services', { method: 'POST', body: json(body) }),
  updateService: (id: string, body: Partial<Omit<CatalogService, 'id'>>) => request<Catalog>(`/catalog/services/${segment(id)}`, {
    method: 'PATCH', body: json(body),
  }),
  getPortal: (token: string) => request<PortalData>(`/portal/${segment(token)}`),
  portalAnswer: (token: string, clarificationId: string, answer: string) => request<Clarification>(`/portal/${segment(token)}/clarifications/${segment(clarificationId)}/answer`, {
    method: 'POST', body: json({ answer }),
  }),
  portalRespond: (token: string, decision: 'accepted' | 'declined' | 'revision_requested', comment?: string) =>
    request<{ status: string; handoff_id?: string }>(`/portal/${segment(token)}/response`, {
      method: 'POST', body: json({ decision, comment }),
    }),
}
