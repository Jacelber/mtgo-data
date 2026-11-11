const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {chromium,expect,request}=require('/workspace/mtgo-data/node_modules/@playwright/test');
const root='/workspace/scratch/pages-slimming/extracted', out='/workspace/scratch/pages-slimming';
const types={'.html':'text/html','.js':'text/javascript','.json':'application/json','.css':'text/css','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.webp':'image/webp'};
const server=http.createServer((req,res)=>{let name=decodeURIComponent(new URL(req.url,'http://local').pathname);name=name.replace(/^\/mtgo-data(?=\/)/,'');if(name.endsWith('/'))name+='index.html';const file=path.resolve(root,'.'+name);if(!file.startsWith(root+'/'))return res.writeHead(403).end();try{const data=fs.readFileSync(file);res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'}).end(data)}catch{res.writeHead(404).end()}});
(async()=>{
await new Promise(r=>server.listen(4174,'127.0.0.1',r));
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,proxy:{server:process.env.HTTPS_PROXY||process.env.https_proxy,bypass:'127.0.0.1,localhost'}});
const page=await browser.newPage({viewport:{width:1440,height:1000}}), requests=[],failures=[],errors=[],checks=[];
page.on('request',r=>requests.push(r.url()));page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.url().startsWith('http://127.0.0.1')&&r.status()>=400)failures.push({url:r.url(),status:r.status()})});
const external=await request.newContext({proxy:{server:process.env.HTTPS_PROXY||process.env.https_proxy}});
// Fetch the exact external URL with Node's supplied proxy CA; no fixture or TLS bypass.
await page.route('https://**/*',async route=>{try{const response=await external.get(route.request().url(),{timeout:20000});await route.fulfill({response})}catch(e){await route.abort()}});
const base='http://127.0.0.1:4174/mtgo-data/';
const ready=async(selector)=>{await expect(page.locator(selector).first()).toBeVisible({timeout:20000});await expect(page.locator('#view')).not.toHaveAttribute('aria-busy','true');await expect(page.locator('#view .error-state')).toHaveCount(0)};
const visit=async(url,selector)=>{console.log('visit',url);await page.goto(base+url);await ready(selector);checks.push({url:page.url(),selector})};
try{
await visit('index.html','.landing-environment-row');
await page.screenshot({path:out+'/landing.png',fullPage:true});
for(const fmt of ['standard','modern','pioneer','legacy','pauper']){
 await visit(`index.html?format=${fmt}&product=mtgo-statistics&range=4&lang=en`,'.composition-panel');
 await page.locator('button[data-detail-identity]:visible').first().click();await ready('.deck-detail-row:not(.load-error-row)');
 await visit(`index.html?format=${fmt}&product=mtgo-matchups&range=4&lang=en`,'[data-record]');
}
for(const fmt of ['standard','modern']){
 await visit(`index.html?format=${fmt}&product=mtgo-landing&lang=zh`,'.landing-environment-row');
 const select=page.locator('#landing-feature-week'), options=await select.locator('option').evaluateAll(es=>es.map(e=>e.value));
 expect(options.length).toBeGreaterThan(1);await select.selectOption(options.at(-1));await ready('.landing-feature-item');
 await page.locator('[data-landing-feature-toggle]').first().click();await expect(page.locator('.landing-feature-item.open')).toBeVisible();
 checks.push({history:fmt,week:options.at(-1),opened:true});
 const images=page.locator('.landing-feature-item').first().locator('.landing-feature-cards img');await images.first().scrollIntoViewIfNeeded();expect(await images.count()).toBeGreaterThan(0);
 await expect.poll(()=>images.evaluateAll(es=>es.every(e=>e.complete&&e.naturalWidth>0)),{timeout:20000}).toBe(true);
 checks.push({decodedFeatureImages:await images.count(),format:fmt});
}
await visit('index.html?format=modern&product=mtgo-top8&lang=en','#top8-week');
const weeks=await page.locator('#top8-week option').evaluateAll(es=>es.map(e=>e.value));await page.locator('#top8-week').selectOption(weeks.at(-1));await ready('button[data-top8-detail]');await page.locator('button[data-top8-detail]').first().click();await ready('[data-close-top8]');checks.push({historicalTop8:weeks.at(-1)});
await visit('index.html?format=modern&product=weekly-pickup&week=2026-W33&lang=en','.landing-feature-item');expect(new URL(page.url()).searchParams.get('product')).toBe('mtgo-landing');
const catalog=JSON.parse(fs.readFileSync(root+'/stats/catalog.json'));
for(const fmt of catalog.formats){const p=fmt.products.find(p=>p.id==='tabletop-major-events'&&p.available);if(!p)continue;const index=JSON.parse(fs.readFileSync(root+'/'+p.path));const event=fmt.id==='modern'?'434455':index.default_event_id;
 await visit(`melee/index.html?format=${fmt.id}&product=tabletop-major-events&event=${event}&view=overview&lang=en`,'#tabletop-event');
 await page.locator('button[data-tabletop-detail]:visible').first().click();await ready('.deck-detail-row:not(.load-error-row)');
 if(fmt.id==='modern'){
  await page.locator('[data-tabletop-scope="day2"]').click();await ready('#tabletop-event');
  await page.locator('#tabletop-event').selectOption(index.events.find(e=>e.event_id!==event).event_id);await ready('#tabletop-event');
 }
 await page.locator('[data-tabletop-view="matchup"]').click();await ready('[data-record]');
}
await page.locator('#lang-zh').click();await ready('[data-record]');await page.screenshot({path:out+'/tabletop.png',fullPage:true});
const removed=requests.filter(u=>/\/mtgo-data\/(data|data_raw|reports)(\/|$)|\/fetched\.txt/.test(new URL(u).pathname));
expect(removed).toEqual([]);expect(failures).toEqual([]);expect(errors).toEqual([]);
fs.writeFileSync(out+'/browser-acceptance.json',JSON.stringify({passed:true,checks,requestCount:requests.length,removedPathRequests:removed,localFailures:failures,pageErrors:errors,requests},null,2));
console.log(JSON.stringify({passed:true,checks:checks.length,requestCount:requests.length}));
}catch(e){fs.writeFileSync(out+'/browser-acceptance-failure.json',JSON.stringify({error:String(e),url:page.url(),checks,requests,failures,errors},null,2));await page.screenshot({path:out+'/browser-failure.png',fullPage:true});throw e}finally{await external.dispose();await browser.close();server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
