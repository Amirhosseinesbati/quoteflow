import type { Brief, ProposalField, QuoteVersion } from '../lib/types'
import { money, shortDate } from '../lib/format'

const sections: Array<[ProposalField, string]> = [
  ['objectives', 'Objectives'], ['scope', 'Scope of work'], ['deliverables', 'Deliverables'],
  ['exclusions', 'Exclusions'], ['assumptions', 'Assumptions'], ['schedule', 'Schedule'],
  ['milestones', 'Milestones'], ['client_responsibilities', 'Your part'], ['acceptance_steps', 'Next steps'],
]

export const proposalFields = sections

export function ProposalPaper({ version, brief, clientName }: { version: QuoteVersion; brief?: Brief; clientName?: string }) {
  const client = clientName || brief?.company_name || 'Your team'
  return <article className="proposal-paper" aria-label={`${version.label} proposal preview`}>
    <header className="paper-meta">
      <div className="paper-logo">ARC <span>&</span> FIELD<br /><span className="text-[9px] tracking-[.2em] font-sans font-semibold text-[#8a8f87]">STUDIO</span></div>
      <div className="text-right text-[9px] leading-[1.65] text-[#959b92] uppercase tracking-[.13em]">
        Proposal / QF-{String(version.number).padStart(3, '0')}<br />{shortDate(version.created_at)}<br />Version {version.number}
      </div>
    </header>
    <div className="eyebrow mt-9">A proposal prepared for {client}</div>
    <h1 className="paper-title">Making room<br />for what’s next.</h1>
    <p className="paper-intro">{version.proposal?.executive_summary || 'A considered plan, carefully scoped around your goals.'}</p>
    <div className="mt-10">
      {sections.map(([key, title]) => {
        const value = version.proposal?.[key]
        if (!value) return null
        return <section className="paper-section" key={key}>
          <h3>{title}</h3>{Array.isArray(value) ? <ul className="list-disc pl-4 text-[11px] leading-[1.7] text-[#414a41] space-y-1">{value.map((item, index) => <li key={`${key}-${index}`}>{item}</li>)}</ul> : <p>{value}</p>}
        </section>
      })}
    </div>
    <section className="mt-7" aria-label="Investment details">
      <div className="eyebrow mb-2">Investment</div>
      <table className="paper-table"><thead><tr><th>Service & assumption</th><th>Qty</th><th>Amount</th></tr></thead>
        <tbody>{version.lines.map((line) => <tr key={line.id}>
          <td><strong className="font-semibold text-[#333b33]">{line.service_name}</strong>{line.assumption && <div className="text-[#92988e] mt-1 leading-[1.5]">{line.assumption}</div>}</td>
          <td>{line.quantity}</td><td>{money(line.line_total)}</td>
        </tr>)}</tbody>
      </table>
      <div className="paper-totals">
        <div className="paper-total-row"><span>Subtotal</span><span>{money(version.subtotal)}</span></div>
        {Number(version.discount_amount) > 0 && <div className="paper-total-row"><span>Discount ({version.discount_percent}%)</span><span>−{money(version.discount_amount)}</span></div>}
        {Number(version.contingency_amount) > 0 && <div className="paper-total-row"><span>Contingency</span><span>{money(version.contingency_amount)}</span></div>}
        {Number(version.tax_amount) > 0 && <div className="paper-total-row"><span>Tax</span><span>{money(version.tax_amount)}</span></div>}
        <div className="paper-total-row final"><span>Total</span><span>{money(version.total)}</span></div>
      </div>
    </section>
    <footer className="paper-footer"><span>ARC & FIELD STUDIO · SYNTHETIC DEMO PROPOSAL</span><span>Prepared with care · {client}</span></footer>
  </article>
}
