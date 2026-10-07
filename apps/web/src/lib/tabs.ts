import type { KeyboardEvent } from 'react'

/** Native buttons retain activation; arrows move focus and selection within a tablist. */
export function onTabKeyDown(event: KeyboardEvent<HTMLElement>) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  const tabs = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]:not(:disabled)'))
  const current = tabs.findIndex((tab) => tab === event.target)
  if (current < 0 || tabs.length < 2) return
  event.preventDefault()
  const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (current + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length
  tabs[index].focus(); tabs[index].click()
}
