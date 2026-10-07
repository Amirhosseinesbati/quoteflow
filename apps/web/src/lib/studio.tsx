import { createContext, useContext } from 'react'
import type { StudioSettings } from './types'

export const defaultStudio: StudioSettings = {
  studio_name: 'Arc & Field Studio', accent_color: '#b65e4b', currency: 'USD', tax_label: 'Tax',
  default_tax_percent: '0.00', default_contingency_percent: '0.00', approval_discount_threshold: '10.00',
  title_template: "Making room for what's next.",
  summary_template: '{studio} proposes the {package} engagement for {client}, based on the supplied brief and the scope shown below.',
  terms: 'Sample terms: work starts after a separate services agreement and agreed deposit. This proposal is not legal advice or a certified electronic signature.',
  footer_note: 'Prepared with care',
}

export const StudioContext = createContext({ ...defaultStudio, synthetic: true })
export const useStudio = () => useContext(StudioContext)
export function templateText(text: string, studio: string, client: string, packageName: string) {
  return text.replaceAll('{studio}', studio).replaceAll('{client}', client).replaceAll('{package}', packageName)
}
