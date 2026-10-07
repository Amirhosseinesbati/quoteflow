import type { Brief, ProposalField, QuoteVersion } from '../lib/types'
import { money, shortDate } from '../lib/format'
import { defaultStudio, templateText } from '../lib/studio'
import type { CSSProperties } from 'react'

const sections: Array<[ProposalField, string]> = [
  ['objectives', 'Objectives'], ['scope', 'Scope of work'], ['deliverables', 'Deliverables'],
  ['exclusions', 'Exclusions'], ['assumptions', 'Assumptions'], ['schedule', 'Schedule'],
  ['milestones', 'Milestones'], ['client_responsibilities', 'Your part'], ['acceptance_steps', 'Next steps'],
  ['terms', 'Terms & start conditions'],
]

export const proposalFields = sections

export function ProposalPaper({ version, brief, clientName }: { version: QuoteVersion; brief?: Brief; clientName?: string }) {
  const client = clientName || brief?.company_name || 'Your team'
  const identity = { ...defaultStudio, synthetic: true, ...version.proposal?._document }
  const price = (value: string | number) => money(value, identity.currency)
  return <article className="proposal-paper" style={{ '--document-accent': identity.accent_color } as CSSProperties} aria-label={`${version.label} proposal preview`}>
    <header className="paper-meta">
      <div className="paper-logo">{identity.studio_name}</div>
      <div className="text-right text-[9px] leading-[1.65] text-[#626d60] uppercase tracking-[.13em]">
        Proposal / QF-{String(version.number).padStart(3, '0')}<br />{shortDate(version.created_at)}<br />Version {version.number}
      </div>
    </header>
    <div className="eyebrow mt-9">A proposal prepared for {client}</div>
    <h2 className="paper-title">{templateText(identity.title_template, identity.studio_name, client, version.label.toLowerCase())}</h2>
    <p className="paper-intro">{version.proposal?.executive_summary || 'A considered plan, carefully scoped around your goals.'}</p>
    <div className="mt-10">
      {sections.map(([key, title]) => {
        const value = version.proposal?.[key]
        if (!value) return null
        return <section className="paper-section" key={key}>
          <h3>{title}</h3>{Array.isArray(value) ? key === 'milestones' || key === 'acceptance_steps' ? <ol className="paper-list numbered">{value.map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}</ol> : <ul className="paper-list">{value.map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}</ul> : <p>{value}</p>}
        </section>
      })}
    </div>
    <section className="mt-7" aria-label="Investment details">
      <div className="eyebrow mb-2">Investment</div>
      <table className="paper-table"><caption className="sr-only">Investment in {identity.currency}, using the approved catalog rates</caption><thead><tr><th scope="col">Service & assumption</th><th scope="col">Qty</th><th scope="col">Amount</th></tr></thead>
        <tbody>{version.lines.map((line) => <tr key={line.id}>
          <td><strong className="font-semibold text-[#333b33]">{line.service_name}</strong>{line.assumption && <div className="text-[#626d60] mt-1 leading-[1.5]">{line.assumption}</div>}</td>
          <td>{line.quantity}</td><td>{price(line.line_total)}</td>
        </tr>)}</tbody>
      </table>
      <div className="paper-totals">
        <div className="paper-total-row"><span>Subtotal</span><span>{price(version.subtotal)}</span></div>
        {Number(version.discount_amount) > 0 && <div className="paper-total-row"><span>Discount ({version.discount_percent}%)</span><span>-{price(version.discount_amount)}</span></div>}
        {Number(version.contingency_amount) > 0 && <div className="paper-total-row"><span>Contingency ({version.contingency_percent}%)</span><span>{price(version.contingency_amount)}</span></div>}
        {Number(version.tax_amount) > 0 && <div className="paper-total-row"><span>{identity.tax_label} ({version.tax_percent}%)</span><span>{price(version.tax_amount)}</span></div>}
        <div className="paper-total-row final"><span>Total ({identity.currency})</span><span>{price(version.total)}</span></div>
      </div>
    </section>
    <footer className="paper-footer"><span>{identity.studio_name}{identity.synthetic ? ' · Synthetic demo proposal' : ''}<br />Catalog {version.catalog_version_id?.slice(0, 8)} · Content {version.content_hash?.slice(0, 10)}</span><span>{identity.footer_note} · {client}</span></footer>
  </article>
}
