import { readFile } from 'node:fs/promises'

const source = process.argv[2] || process.env.QUOTEFLOW_OPENAPI_URL || 'http://127.0.0.1:8011/openapi.json'
let schema
if (/^https?:\/\//.test(source)) {
  const response = await fetch(source)
  if (!response.ok) throw new Error(`Unable to load OpenAPI schema (${response.status}) from ${source}`)
  schema = await response.json()
} else {
  schema = JSON.parse(await readFile(source, 'utf8'))
}
const normalized = Object.fromEntries(Object.entries(schema.paths || {}).map(([path, value]) => [path.replace(/\{[^}]+\}/g, '{}'), value]))

const expected = [
  ['get', '/api/health'], ['post', '/api/auth/demo'],
  ['get', '/api/briefs'], ['post', '/api/briefs'], ['post', '/api/briefs/upload'],
  ['get', '/api/briefs/{}'], ['post', '/api/briefs/{}/analyze'],
  ['post', '/api/briefs/{}/clarifications'], ['post', '/api/briefs/{}/clarifications/{}/answer'],
  ['post', '/api/briefs/{}/portal-link'], ['post', '/api/briefs/{}/options'],
  ['get', '/api/quotes/{}'], ['patch', '/api/quotes/{}/versions/{}'],
  ['post', '/api/quotes/{}/versions/{}/price-preview'], ['post', '/api/quotes/{}/versions/{}/submit-review'],
  ['post', '/api/quotes/{}/versions/{}/publish'], ['get', '/api/quotes/{}/versions/{}/pdf'],
  ['get', '/api/quotes/{}/diff'], ['get', '/api/approvals'], ['post', '/api/approvals/{}/decision'],
  ['get', '/api/catalog'], ['post', '/api/catalog/services'], ['patch', '/api/catalog/services/{}'],
  ['get', '/api/portal/{}'], ['post', '/api/portal/{}/clarifications/{}/answer'], ['post', '/api/portal/{}/response'],
]

const missing = expected.filter(([method, path]) => !normalized[path]?.[method]).map(([method, path]) => `${method.toUpperCase()} ${path}`)
const diff = normalized['/api/quotes/{}/diff']?.get
const queryNames = new Set((diff?.parameters || []).filter((parameter) => parameter.in === 'query').map((parameter) => parameter.name))
if (!queryNames.has('from') || !queryNames.has('to')) missing.push('GET quote diff query parameters: from, to')

const componentSchemas = Object.values(schema.components?.schemas || {})
const hasShape = (fields) => componentSchemas.some((component) => fields.every((field) => field in (component.properties || {})))
if (!hasShape(['source_type','text','company_name','contact_name','contact_email'])) missing.push('BriefCreate request fields')
if (!hasShape(['proposal','lines','discount_percent','tax_percent','contingency_percent'])) missing.push('VersionEdit request fields')
if (!hasShape(['code','name','category','description','unit','base_price','active'])) missing.push('ServiceEdit request fields')
if (!hasShape(['decision','comment'])) missing.push('PortalDecision request fields')

if (missing.length) {
  console.error(`OpenAPI/client drift (${missing.length}):\n${missing.map((item) => `  - ${item}`).join('\n')}`)
  process.exitCode = 1
} else {
  console.log(`OpenAPI contract check passed: ${expected.length} route methods and 4 write payload shapes (${source})`)
}
