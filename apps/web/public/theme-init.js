/* Blocking same-origin bootstrap, before application or styles paint. */
(() => {
  let mode = 'dark'
  try {
    const saved = localStorage.getItem('quoteflow-theme')
    if (saved === 'light' || saved === 'dark' || saved === 'system') mode = saved
  } catch { /* Storage is optional. */ }
  let dark = mode !== 'light'
  if (mode === 'system') {
    try { dark = matchMedia('(prefers-color-scheme: dark)').matches } catch { dark = true }
  }
  document.documentElement.dataset.themeMode = mode
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0b101a' : '#eef2f8')
})()
