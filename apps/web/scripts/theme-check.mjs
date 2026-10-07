import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const base = process.env.QUOTEFLOW_URL || 'http://127.0.0.1:4316'
const output = resolve('../../tmp/theme-qa')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ channel: process.env.QUOTEFLOW_BROWSER || 'msedge', headless: true })
const errors = [], checks = [], shots = [], contrastResults = []
async function createContext(options = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: 'light', reducedMotion: 'reduce', ...options })
  context.on('page', (page) => page.on('pageerror', (error) => errors.push(error.message)))
  return context
}
async function theme(page, mode) {
  await page.getByLabel('Appearance', { exact: true }).selectOption(mode)
  await page.waitForFunction((expected) => document.documentElement.dataset.themeMode === expected, mode)
}
async function resolved(page) { return page.evaluate(() => document.documentElement.dataset.theme) }
async function shot(page, name, width = 1440) {
  await page.setViewportSize({ width, height: width < 600 ? 844 : 1000 })
  await page.evaluate(()=>window.scrollTo(0,0))
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${name}: horizontal page overflow`)
  if(width<600) {
    const small=await page.locator('.btn,.icon-btn,.studio-tab,.theme-control select').evaluateAll((nodes)=>nodes.filter((node)=>node.getBoundingClientRect().width && node.getBoundingClientRect().height && !node.disabled).filter((node)=>node.getBoundingClientRect().height<44).map((node)=>({text:node.textContent.trim(),height:node.getBoundingClientRect().height})))
    assert.deepEqual(small,[],`${name}: small mobile control`)
  }
  await page.screenshot({ path: `${output}/${name}.png`, fullPage: true, animations: 'disabled' })
  shots.push(name)
  if(name.startsWith('05-workbench-')) {
    await page.evaluate(()=>window.scrollTo(0,0))
    await page.screenshot({path:`${output}/${name}-viewport.png`,animations:'disabled'})
    shots.push(name+'-viewport')
  }
  if(name.startsWith('06-workbench-mobile-')) {
    await page.waitForFunction(()=>{const group=document.querySelector('.option-grid'),selected=group?.querySelector('[aria-pressed="true"]');if(!group||!selected)return false;const a=group.getBoundingClientRect(),b=selected.getBoundingClientRect();return b.left>=a.left-1&&b.right<=a.right+1})
    await page.locator('.compare-heading').scrollIntoViewIfNeeded()
    await page.screenshot({path:`${output}/${name}-viewport.png`,animations:'disabled'})
    shots.push(name+'-viewport')
  }
}
async function data(response, status = 200) { assert.equal(response.status(), status, await response.text()); return response.json() }
async function contrast(page, name) {
  const results = await page.evaluate(() => {
    const rgb = (value) => (value.match(/[\d.]+/g) || []).map(Number)
    const lum = (color) => color.slice(0,3).map((v) => { const n=v/255; return n<=.04045 ? n/12.92 : ((n+.055)/1.055)**2.4 }).reduce((sum,v,i) => sum+v*[.2126,.7152,.0722][i],0)
    const nodes = [...document.querySelectorAll('.page-title,.page-subtitle,.eyebrow,.field label,.field-help,.alert,.btn-primary:not(:disabled),.nav-link.active,.option-name,.option-price,.quote-context-strip dd,.paper-section p,.paper-list li,.paper-section h3,.paper-footer,.theme-control select')]
    return nodes.filter((node) => node.getBoundingClientRect().width && node.getBoundingClientRect().height && !node.closest('[inert]')).map((node) => {
      const style=getComputedStyle(node); let parent=node; let background=[0,0,0,0]
      while(parent && background[3] !== 1) { background=rgb(getComputedStyle(parent).backgroundColor); if(background.length===3) background.push(1); parent=parent.parentElement }
      const color=rgb(style.color), a=lum(color), b=lum(background)
      const ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05)
      const large=parseFloat(style.fontSize)>=24 || (parseFloat(style.fontSize)>=18.66 && Number(style.fontWeight)>=700)
      return { text:node.textContent.trim().slice(0,60), ratio:Number(ratio.toFixed(2)), minimum:large?3:4.5 }
    })
  })
  const failed = results.filter((item) => item.ratio < item.minimum)
  contrastResults.push({ name, sampled: results.length, minimumRatio: Math.min(...results.map((item) => item.ratio)), failures: failed })
  assert.deepEqual(failed, [], `${name}: sampled text contrast`)
}
try {
  const context=await createContext(), page=await context.newPage()
  await page.goto(base, { waitUntil: 'networkidle' })
  assert.equal(await resolved(page), 'dark', 'Fresh fallback is Dark, even with light OS')
  await shot(page,'01-entry-dark')
  await theme(page,'light'); await shot(page,'02-entry-light'); await contrast(page,'entry-light')
  await page.getByRole('button',{name:'admin',exact:true}).click()
  await page.getByRole('button',{name:'Enter demo workspace',exact:true}).click()
  await page.getByLabel('CLIENT NOTE OR PROJECT BRIEF *').fill('An unsaved brief remains intact while appearance changes.')
  await page.getByLabel('COMPANY (OPTIONAL)').fill('Aster Systems')
  await theme(page,'dark'); await shot(page,'03-intake-dark'); await contrast(page,'intake-dark')
  assert.equal(await page.getByLabel('COMPANY (OPTIONAL)').inputValue(),'Aster Systems')
  await page.emulateMedia({colorScheme:'light'}); assert.equal(await resolved(page),'dark')
  await theme(page,'system'); assert.equal(await resolved(page),'light')
  await page.emulateMedia({colorScheme:'dark'}); await page.waitForFunction(() => document.documentElement.dataset.theme==='dark')
  await theme(page,'light'); await page.emulateMedia({colorScheme:'dark'}); assert.equal(await resolved(page),'light')
  assert.equal(await page.getByLabel('CLIENT NOTE OR PROJECT BRIEF *').inputValue(),'An unsaved brief remains intact while appearance changes.')
  await shot(page,'04-intake-light'); await contrast(page,'intake-light')
  await page.reload({waitUntil:'networkidle'}); assert.equal(await resolved(page),'light')
  checks.push('fresh Dark fallback, persistence, explicit OS independence, live System, intact intake edits')
  console.log('Theme preference and intake state passed')

  const brief=await data(await context.request.post(`${base}/api/briefs`,{data:{company_name:'Aster Systems',text:'We need a five-page website with analytics in twelve weeks. Our budget is $20,000. Final approved copy and photography are available.'}}),201)
  const analyzed=await data(await context.request.post(`${base}/api/briefs/${brief.id}/analyze`))
  for(const question of analyzed.clarifications) await data(await context.request.post(`${base}/api/briefs/${brief.id}/clarifications/${question.id}/answer`,{data:{answer:'Twelve weeks; $20,000; final content supplied.'}}))
  const options=await data(await context.request.post(`${base}/api/briefs/${brief.id}/options`))
  await page.goto(`${base}?view=studio&brief=${brief.id}`,{waitUntil:'networkidle'})
  await page.getByRole('article',{name:'Recommended proposal preview'}).waitFor()
  let paperBaseline
  for(const mode of ['dark','light']) {
    await theme(page,mode)
    const paper=await page.locator('.proposal-paper').evaluate((node) => ({text:node.innerText,color:getComputedStyle(node).color,background:getComputedStyle(node).backgroundColor,width:node.getBoundingClientRect().width,height:node.getBoundingClientRect().height}))
    if(paperBaseline) assert.deepEqual(paper,paperBaseline,'Document palette/geometry changed with theme')
    else paperBaseline=paper
    await shot(page,`05-workbench-${mode}`); await contrast(page,`workbench-${mode}`)
    await shot(page,`06-workbench-mobile-${mode}`,390)
    await page.setViewportSize({width:1440,height:1000})
  }
  const tab=page.getByRole('tab',{name:'Document preview',exact:true})
  await tab.focus(); await page.keyboard.press('ArrowRight')
  assert.equal(await page.getByRole('tab',{name:/Edit scope/}).getAttribute('aria-selected'),'true')
  const summary='A deliberate scope for Aster Systems, retained across every appearance change.'
  await page.getByLabel('EXECUTIVE SUMMARY',{exact:true}).fill(summary)
  await page.getByLabel('DISCOUNT %',{exact:true}).fill('9')
  await page.getByRole('button',{name:'Preview price',exact:true}).click()
  await page.getByText('Server-calculated preview',{exact:true}).waitFor()
  const price=await page.locator('.pricing-editor').innerText()
  let mutations=0
  const track=(request) => { if(['POST','PUT','PATCH','DELETE'].includes(request.method()) && request.url().includes('/api/')) mutations++ }
  page.on('request',track)
  for(const mode of ['dark','light']) {
    await theme(page,mode)
    assert.equal(await page.getByLabel('EXECUTIVE SUMMARY',{exact:true}).inputValue(),summary)
    assert.equal(await page.getByLabel('DISCOUNT %',{exact:true}).inputValue(),'9')
    assert.equal(await page.locator('.pricing-editor').innerText(),price)
    await shot(page,`07-editor-${mode}`); await contrast(page,`editor-${mode}`)
  }
  assert.equal(mutations,0,'Appearance triggered a write to the API'); page.off('request',track)
  await page.getByLabel('DISCOUNT %',{exact:true}).fill('101')
  await page.getByRole('button',{name:'Preview price',exact:true}).click()
  await page.getByRole('alert').filter({hasText:'between 0 and 100'}).waitFor()
  for(const mode of ['dark','light']) { await theme(page,mode); await shot(page,`08-price-error-mobile-${mode}`,390) }
  await page.setViewportSize({width:1440,height:1000})
  await page.getByRole('button',{name:/Option 01/}).click()
  const dialog=page.getByRole('dialog',{name:'Keep your edits?'})
  await dialog.waitFor(); assert.equal(await dialog.evaluate((node)=>node.contains(document.activeElement)),true)
  await page.keyboard.press('Escape'); await dialog.waitFor({state:'hidden'})
  assert.equal(await page.getByLabel('DISCOUNT %',{exact:true}).inputValue(),'101')
  await page.getByLabel('DISCOUNT %',{exact:true}).fill('9')
  const [revisionResponse]=await Promise.all([page.waitForResponse((r)=>r.request().method()==='PATCH' && r.url().includes('/versions/')),page.getByRole('button',{name:'Save as new version',exact:true}).click()])
  const revision=await data(revisionResponse)
  const [reviewResponse]=await Promise.all([page.waitForResponse((r)=>r.url().endsWith('/submit-review')),page.getByRole('button',{name:'Request approval',exact:true}).click()])
  const approval=await data(reviewResponse)
  await theme(page,'dark'); await theme(page,'light')
  const pending=await data(await context.request.get(`${base}/api/quotes/${options.quote_id}`))
  assert.equal(pending.versions.find((v)=>v.id===revision.id).status,'pending_review')
  await page.getByRole('button',{name:'Review queue',exact:true}).click()
  await theme(page,'dark')
  await page.locator('.divide-y > div').filter({hasText:revision.id.slice(0,8)}).first().getByRole('button',{name:'Review',exact:true}).click()
  await shot(page,'09-approval-dialog-dark')
  await page.getByRole('button',{name:'Approve version',exact:true}).click()
  await page.goto(`${base}?view=studio&brief=${brief.id}`,{waitUntil:'networkidle'})
  await page.getByRole('button',{name:/^v4/}).click()
  const [publishedResponse]=await Promise.all([page.waitForResponse((r)=>r.url().endsWith('/publish')),page.getByRole('button',{name:'Generate PDF & review link',exact:true}).click()])
  const published=await data(publishedResponse)
  const root=`${base}/api/quotes/${options.quote_id}/versions/${revision.id}`
  let pdfBaseline
  for(const mode of ['dark','light']) {
    await theme(page,mode)
    const response=await context.request.get(root+'/pdf'); assert.equal(response.status(),200)
    const pdf=await response.body(); await writeFile(`${output}/proposal-${mode}.pdf`,pdf)
    if(pdfBaseline) assert.deepEqual(pdf,pdfBaseline,'Appearance changed exported PDF bytes')
    else pdfBaseline=pdf
  }
  checks.push('document palette/geometry invariant, keyboard tabs, quote edits/pricing preserved, no theme writes, server error, native dialog, approval state, identical PDF bytes')
  console.log('Quote editor, approval and PDF invariants passed')

  const customer=await createContext({viewport:{width:390,height:844}}), review=await customer.newPage()
  await review.goto(`${base}/portal/${published.token}`,{waitUntil:'networkidle'})
  await review.getByRole('button',{name:'Request revisions',exact:true}).click()
  await review.getByLabel('WHAT WOULD YOU LIKE CHANGED?',{exact:true}).fill('Keep this draft customer response while testing appearance.')
  await review.keyboard.press('Escape')
  for(const mode of ['dark','light']) {
    await theme(review,mode); assert.equal(new URL(review.url()).pathname,`/portal/${published.token}`)
    await shot(review,`10-customer-mobile-${mode}`,390); await contrast(review,`customer-${mode}`)
  }
  await review.getByRole('button',{name:'Request revisions',exact:true}).click()
  assert.equal(await review.getByLabel('WHAT WOULD YOU LIKE CHANGED?',{exact:true}).inputValue(),'Keep this draft customer response while testing appearance.')
  await review.keyboard.press('Escape')
  await review.getByRole('button',{name:'Accept proposal',exact:true}).click()
  await review.getByRole('button',{name:'Confirm response',exact:true}).click()
  await review.getByText('This review is accepted.',{exact:false}).waitFor()
  await shot(review,'11-customer-accepted-light',390); await customer.close()
  checks.push('customer route and response draft preserved; actual acceptance/handoff')

  await page.getByRole('button',{name:'Studio settings',exact:true}).click()
  for(const mode of ['dark','light']) { await theme(page,mode); await shot(page,`12-settings-${mode}`); await contrast(page,`settings-${mode}`) }
  await page.getByRole('button',{name:'Service catalog',exact:true}).click()
  for(const mode of ['dark','light']) { await theme(page,mode); await shot(page,`13-catalog-${mode}`); await contrast(page,`catalog-${mode}`) }
  await page.getByRole('button',{name:'Briefs',exact:true}).click()
  for(const mode of ['dark','light']) { await theme(page,mode); await shot(page,`14-briefs-${mode}`) }
  await page.route('**/api/briefs',(route)=>route.fulfill({status:503,body:'Synthetic offline fixture'}))
  await page.reload({waitUntil:'networkidle'}); await page.getByRole('alert').waitFor()
  await shot(page,'15-server-error-light'); await page.unroute('**/api/briefs')
  assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior),'auto','Reduced motion did not suppress smooth scroll')
  await context.close()

  // Check before React is allowed to execute, under a CSP that forbids inline scripts.
  for(const mode of ['light','dark','system','invalid']) {
    const boot=await createContext({colorScheme:'light'})
    await boot.addInitScript((saved)=>{try{localStorage.setItem('quoteflow-theme',saved)}catch{/* about:blank has no origin */}},mode)
    const initial=await boot.newPage()
    await initial.route('**/src/main.tsx',(route)=>route.abort())
    await initial.route(base+'/',async(route)=>{
      const response=await route.fetch()
      // Isolate the real bootstrap from Vite's development-only inline refresh preamble.
      const html=(await response.text()).replace(/<script[^>]*type="module"[^>]*>[\s\S]*?<\/script>/g,'')
      await route.fulfill({response,body:html,headers:{...response.headers(),'content-security-policy':"script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' ws:"}})
    })
    await initial.goto(base,{waitUntil:'domcontentloaded'})
    assert.equal(await initial.locator('#root').innerHTML(),'')
    assert.equal(await resolved(initial),mode==='light'||mode==='system'?'light':'dark',`Prepaint ${mode}`)
    assert.equal(await initial.evaluate(()=>getComputedStyle(document.documentElement).backgroundColor),mode==='light'||mode==='system'?'rgb(238, 242, 248)':'rgb(11, 16, 26)',`Prepaint canvas ${mode}`)
    await boot.close()
  }
  const blocked=await createContext()
  await blocked.addInitScript(()=>{ for(const method of ['getItem','setItem','removeItem']) Storage.prototype[method]=()=>{throw new DOMException('Storage blocked','SecurityError')} })
  const blockedPage=await blocked.newPage(); await blockedPage.goto(base,{waitUntil:'networkidle'})
  assert.equal(await resolved(blockedPage),'dark'); await theme(blockedPage,'light'); assert.equal(await resolved(blockedPage),'light')
  await blockedPage.getByRole('button',{name:'Enter demo workspace',exact:true}).click()
  await blockedPage.getByLabel('CLIENT NOTE OR PROJECT BRIEF *').waitFor(); await blocked.close()
  checks.push('all preferences applied before React under self-only script CSP, invalid preference fallback, blocked storage usable, reduced motion, error retry screen, contrast sampling')
  assert.deepEqual(errors,[])
  await writeFile(`${output}/result.json`,JSON.stringify({passed:true,screenshots:shots.length,pageErrors:errors,checks,contrastResults,briefId:brief.id,quoteId:options.quote_id,revisionId:revision.id,approvalId:approval.id,shots},null,2))
  console.log(`Theme/workbench checks passed: ${shots.length} screenshots, zero page errors. Evidence: ${output}`)
} finally { await browser.close() }
