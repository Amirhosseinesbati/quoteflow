import { mkdir } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const projectRoot = resolve(fileURLToPath(new URL('../../../', import.meta.url)))
const theme = process.env.QUOTEFLOW_THEME
const screenshotDir = join(projectRoot, 'tmp', theme ? `browser-check-${theme}` : 'browser-check')
await mkdir(screenshotDir, { recursive: true })
const baseUrl = process.env.QUOTEFLOW_URL || 'http://127.0.0.1:5173/'
const browser = await chromium.launch({
  ...(process.env.QUOTEFLOW_BROWSER ? { channel: process.env.QUOTEFLOW_BROWSER } : {}),
  headless: true,
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
if (theme) await page.context().addInitScript((mode) => { try { localStorage.setItem('quoteflow-theme', mode) } catch { /* about:blank has no origin */ } }, theme)
const errors = []
page.on('pageerror', (error) => errors.push(error.message))

async function shot(name, width, height = 900) {
  await page.setViewportSize({ width, height })
  await page.waitForTimeout(250)
  const path = join(screenshotDir, name)
  await page.screenshot({ path, fullPage: true, animations: 'disabled' })
  console.log(`Screenshot: ${path}`)
}

async function click(name) {
  await page.getByRole('button', { name, exact: true }).click()
}

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  console.log('Initial page:', page.url(), (await page.locator('body').innerText()).slice(0, 500))
  await page.getByRole('button', { name: 'Enter demo workspace' }).waitFor({ state: 'visible', timeout: 15_000 })
  await shot('01-demo-entry-1440.png', 1440)
  await click('admin')
  await click('Enter demo workspace')
  await page.getByLabel('CLIENT NOTE OR PROJECT BRIEF *').waitFor({ state: 'visible' })
  await shot('02-intake-1440.png', 1440)
  await page.getByLabel('CLIENT NOTE OR PROJECT BRIEF *').fill('Smoke Example Studio needs a five-page responsive website, analytics, and a CRM contact sync in twelve weeks. Our working budget is $18,000–$30,000. We can supply approved photography and a draft sitemap. We need a clear content owner and two review rounds. Please address Morgan Test at morgan@smoke-example.test.')
  await page.getByLabel('COMPANY (OPTIONAL)').fill('Smoke Example Studio')
  await page.getByLabel('CONTACT NAME (OPTIONAL)').fill('Morgan Test')
  await page.getByLabel('CONTACT EMAIL (OPTIONAL)').fill('morgan@smoke-example.test')
  await click('Create brief')
  await page.getByRole('button', { name: 'Analyze brief' }).waitFor({ state: 'visible' })
  const briefId = new URL(page.url()).searchParams.get('brief')
  if (!briefId) throw new Error('Brief route did not include its server-owned ID')
  await click('Analyze brief')
  await page.getByRole('tab', { name: /Requirements/ }).click()
  await shot('03-evidence-1440.png', 1440)
  await page.getByRole('tab', { name: /Clarifications/ }).click()
  const existingQuestions = await page.locator('.clarification-item').count()
  if (existingQuestions < 2) {
    let count = existingQuestions
    for (const question of ['Who will supply the final website copy?', 'Do you need the CRM contact sync to be one-way or two-way?'].slice(0, 2 - existingQuestions)) {
      await page.getByLabel('ADD A TARGETED QUESTION').fill(question)
      await page.waitForFunction(() => !document.querySelector('#new-question')?.closest('form')?.querySelector('button[type="submit"]')?.disabled)
      await click('Add question')
      count += 1
      await page.waitForFunction((expected) => document.querySelectorAll('.clarification-item').length >= expected, count)
    }
  }
  await shot('04-clarifications-1024.png', 1024)
  await click('Create customer link')
  const clarificationLink = await page.locator('a[href*="/portal/"]').last().getAttribute('href')
  if (!clarificationLink) throw new Error('Customer clarification link was not rendered')
  const customerContext = await browser.newContext({ viewport: { width: 1024, height: 900 } })
  if (theme) await customerContext.addInitScript((mode) => { try { localStorage.setItem('quoteflow-theme', mode) } catch { /* about:blank has no origin */ } }, theme)
  const customerPage = await customerContext.newPage()
  customerPage.on('pageerror', (error) => errors.push(error.message))
  try {
    await customerPage.goto(clarificationLink, { waitUntil: 'networkidle' })
    await customerPage.getByRole('heading', { name: 'A few thoughtful questions.' }).waitFor()
    await customerPage.screenshot({ path: join(screenshotDir, '04b-customer-clarification-1024.png'), fullPage: true, animations: 'disabled' })
    const customerAnswers = ['Our marketing lead will supply final approved website copy.', 'A one-way sync from the website contact form into the CRM is sufficient.']
    for (let index = 0; index < customerAnswers.length; index += 1) {
      const openForms = customerPage.locator('.clarification-item form')
      const previous = await openForms.count()
      if (!previous) throw new Error('Customer clarification form closed before both answers were saved')
      await openForms.first().getByLabel('YOUR ANSWER').fill(customerAnswers[index])
      await openForms.first().getByRole('button', { name: 'Save answer' }).click()
      await customerPage.waitForFunction((expected) => document.querySelectorAll('.clarification-item form').length < expected, previous)
    }
  } finally {
    await customerContext.close()
  }
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: /Clarifications/ }).click()
  await page.getByText('Our marketing lead will supply final approved website copy.').waitFor()
  await page.getByText('A one-way sync from the website contact form into the CRM is sufficient.').waitFor()
  await page.getByRole('button', { name: 'Generate 3 options' }).click()
  await page.getByRole('group', { name: 'Scope options' }).waitFor({ state: 'visible', timeout: 30_000 })
  await shot('05-options-1440.png', 1440)
  await page.getByRole('tab', { name: /Edit scope/ }).click()
  const firstQuantity = page.locator('input[id^="line-qty-"]').first()
  await firstQuantity.fill(String(Number(await firstQuantity.inputValue()) + 1))
  await page.getByLabel('DISCOUNT %').fill('25')
  await click('Preview price')
  await page.waitForTimeout(300)
  if (await page.locator('.alert.error').count()) throw new Error(`Price preview failed: ${await page.locator('.alert.error').first().innerText()}`)
  await shot('06-price-review-1024.png', 1024)
  const [saveResponse] = await Promise.all([page.waitForResponse((response) => response.request().method() === 'PATCH' && response.url().includes('/versions/')), click('Save as new version')])
  console.log('Save response:', saveResponse.status(), (await saveResponse.text()).slice(0, 500))
  await page.waitForTimeout(500)
  console.log('After save:', (await page.locator('body').innerText()).slice(0, 1200))
  await shot('06b-after-save-1024.png', 1024)
  if (await page.locator('.alert.error').count()) throw new Error(`Version save failed: ${await page.locator('.alert.error').first().innerText()}`)
  await page.getByRole('tab', { name: 'Scope diff' }).click()
  const previousRecommended = await page.locator('#compare-version option').filter({ hasText: /Version 2.*Recommended/ }).getAttribute('value')
  if (!previousRecommended) throw new Error('Previous recommended version is unavailable for comparison')
  await page.locator('#compare-version').selectOption(previousRecommended)
  await page.getByText('Changed services').waitFor()
  await page.locator('.soft-card').filter({ hasText: /→/ }).first().waitFor()
  if ((await page.locator('.panel').last().innerText()).includes('undefined')) throw new Error('Scope diff rendered an undefined service or price')
  await page.getByRole('tab', { name: 'Document preview' }).click()
  const [submitResponse] = await Promise.all([page.waitForResponse((response) => response.url().includes('/submit-review') && response.request().method() === 'POST'), page.getByRole('button', { name: 'Request approval' }).click()])
  if (!submitResponse.ok()) throw new Error(`Approval request failed: ${submitResponse.status()} ${await submitResponse.text()}`)
  const approval = await submitResponse.json()
  await page.getByRole('button', { name: 'Review queue' }).click()
  await shot('07-approval-1440.png', 1440)
  await page.locator('.divide-y > div').filter({ hasText: approval.quote_version_id.slice(0, 8) }).first().getByRole('button', { name: 'Review' }).click()
  await click('Approve version')
  await page.goto(`${baseUrl}?view=studio&brief=${briefId}`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /^v4/ }).click()
  await page.getByRole('button', { name: 'Generate PDF & review link' }).click()
  await shot('08-proposal-mobile-390.png', 390, 844)
  const portalLink = await page.locator('a[href*="/portal/"]').last().getAttribute('href')
  if (!portalLink) throw new Error('Customer review link was not rendered')
  await page.goto(portalLink, { waitUntil: 'networkidle' })
  await shot('09-customer-review-1024.png', 1024)
  await click('Accept proposal')
  await click('Confirm response')
  await shot('10-accepted-mobile-390.png', 390, 844)
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`)
  console.log('Browser journey passed: brief → unauthenticated customer clarification → options → version → approval → publish → acceptance')
} finally {
  await browser.close()
}
