// Run with node test-guide.cjs OUTPUT_PREFIX [PLAYWRIGHT_MODULE_PATH].
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.argv[3]||'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:960}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(path.join(__dirname,'Notation-guide.html')).href);
  const count=await page.locator('main section').count();assert(count>=44);
  for(const query of ['css_encoder','stabilizer_correction','PyQASM','css_state','XPowGate','global_shift','hellinger_fidelity','binary numerals','spin.x','root_fidelity','Hermitian matrix order']) {
   await page.locator('#search').fill(query);
   const sections=page.locator('main section:not([hidden])');assert((await sections.count())>0,query);
   assert.equal(await page.locator('nav a:not([hidden])').count(),await sections.count());
   // The guide matches every search word, not necessarily one contiguous phrase.
   const words=query.toLowerCase().trim().split(/\s+/);
   for(const text of await sections.allTextContents())assert(words.every(word=>text.toLowerCase().includes(word)));
  }
  await page.locator('#search').fill('css_encoder');
  await page.screenshot({path:process.argv[2]+'.png',fullPage:true});
  await page.locator('nav a:not([hidden])').first().click();
  assert(page.url().includes('#encode-logical-states-with-css-codes'));
  await page.locator('#search').fill('no-such-notation-topic-98765');
  assert.equal(await page.locator('main section:not([hidden])').count(),0);
  assert(await page.locator('#empty').isVisible());
  await page.locator('#clear').click();assert.equal(await page.locator('main section:not([hidden])').count(),count);
  await page.keyboard.press('Escape');
  assert.deepEqual(errors,[]);
  console.log('PASS: browser search, matching navigation, new-topic anchors, empty results and reset across '+count+' topics.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
