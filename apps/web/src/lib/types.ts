export type Role = 'admin' | 'operator' | 'viewer'
export type Workspace = 'arc-field-demo' | 'arc-field-isolation'

export interface Session {
  user: { id?: string; name?: string; email?: string; role?: Role }
  workspace: string | { id: string; name?: string }
  role: Role
}

export interface Health {
  status: string
  mode: string
}

export interface Requirement {
  id: string
  text: string
  kind: string
  evidence: string
  start?: number | null
  end?: number | null
  confidence?: number | null
}

export interface Clarification {
  id: string
  question: string
  answer?: string | null
  status: string
}

export interface Brief {
  id: string
  source_type: string
  text: string
  company_name?: string | null
  contact_name?: string | null
  contact_email?: string | null
  status?: string
  created_at?: string
  updated_at?: string
  quote_id?: string | null
  requirements?: Requirement[]
  clarifications?: Clarification[]
  extracted?: Record<string, unknown> | null
}

export interface Proposal {
  executive_summary: string
  objectives: string | string[]
  scope: string | string[]
  deliverables: string | string[]
  exclusions: string | string[]
  assumptions: string | string[]
  schedule: string | string[]
  milestones: string | string[]
  client_responsibilities: string | string[]
  acceptance_steps: string | string[]
}

export type ProposalField = keyof Proposal

export interface QuoteLine {
  id: string
  service_id: string
  service_name: string
  quantity: string | number
  unit_price: string
  assumption: string
  line_total: string
}

export interface QuoteLineEdit {
  service_id: string
  service_name: string
  quantity: string
  assumption: string
}

export interface QuoteVersion {
  id: string
  number: number
  label: string
  status: string
  proposal: Proposal
  lines: QuoteLine[]
  discount_percent: string
  tax_percent: string
  contingency_percent: string
  subtotal: string
  discount_amount: string
  tax_amount: string
  contingency_amount: string
  total: string
  approval_required: boolean
  approved: boolean
  created_at?: string
  catalog_version?: string | number
}

export interface Quote {
  id: string
  brief_id: string
  versions: QuoteVersion[]
}

export interface PricePreview {
  lines: QuoteLine[]
  discount_percent: string
  tax_percent: string
  contingency_percent: string
  subtotal: string
  discount_amount: string
  tax_amount: string
  contingency_amount: string
  total: string
  approval_required?: boolean
}

export interface Approval {
  id: string
  quote_version_id: string
  status: string
  note?: string | null
  created_at?: string
  quote_id?: string
  brief_id?: string
  client_name?: string
  total?: string
}

export interface CatalogService {
  id: string
  code: string
  name: string
  category: string
  description: string
  unit: string
  base_price: string
  active: boolean
}

export interface Catalog {
  version: string | number
  services: CatalogService[]
}

export interface PublishResult {
  token: string
  portal_url: string
  pdf_url: string
}

export interface PortalClarification {
  kind: 'clarification'
  brief: Brief
  clarifications: Clarification[]
  client_name?: string
  expires_at?: string
  status?: string
}

export interface PortalReview {
  kind: 'review'
  quote_version: QuoteVersion
  client_name: string
  expires_at: string
  status: string
}

export type PortalData = PortalClarification | PortalReview

export interface QuoteDiff {
  added_lines: string[]
  removed_lines: string[]
  changed_lines: Array<{
    service: string
    old_quantity: string
    new_quantity: string
    old_total: string
    new_total: string
  }>
  total_delta: string
  proposal_changes: string[]
}
