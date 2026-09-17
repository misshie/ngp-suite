import type { MondoTerm } from '@/stores/app'

/** Primary language subtag: ja, en, zh, pt, … */
export function localeLanguageTag (locale: string): string {
  return (locale.split('-')[0] || 'en').toLowerCase()
}

export function mondoLabel (
  term: Pick<MondoTerm, 'name' | 'labels'> | null | undefined,
  locale: string,
): string {
  const labels = term?.labels || {}
  const tag = localeLanguageTag(locale)
  return labels[tag] || labels.en || term?.name || ''
}

export function syndromeLabel (
  item: { syndrome_name: string, syndrome_labels?: Record<string, string> },
  locale: string,
): string {
  return mondoLabel({ name: item.syndrome_name, labels: item.syndrome_labels }, locale)
}

export function formatMondoTerm (term: MondoTerm, locale: string): string {
  const label = mondoLabel(term, locale)
  return label ? `${term.id} ${label}` : term.id
}
