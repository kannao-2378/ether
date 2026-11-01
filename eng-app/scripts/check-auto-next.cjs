const {chromium}=require('C:/Users/X/AppData/Local/OpenAI/Codex/runtimes/cua_node/5c41f77a7900391c/bin/node_modules/playwright');
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true});const p=await b.newPage();
 let index=0;const saved=[];
 await p.addInitScript(()=>localStorage.setItem('speech-auto','off'));
 await p.route('**/api/**',async r=>{
  const path=new URL(r.request().url()).pathname;let data={};
  if(path.endsWith('/dashboard'))data={items:[{id:'k',answer:'want to',introduced:1}],history:[],due:1,today_count:saved.length};
  if(path.endsWith('/next'))data={kind:'recall',question_id:'q'+index++,id:'k',prompt:'Recall',answer_length:7};
  if(path.endsWith('/check'))data={correct:true,answer:'want to',explanation:'test',example:'I want to eat.'};
  if(path.endsWith('/answers')){saved.push(r.request().postDataJSON().confidence);data={correct:1,feedback:'Saved',due_at:new Date().toISOString()};}
  await r.fulfill({json:data});
 });
 await p.goto('http://127.0.0.1:5173');await p.waitForSelector('.memo-writing input');
 for(const key of ['1','2','3']){
  if(key!=='3'){await p.locator('.memo-writing input').fill('want to');await p.waitForSelector('.memo-explanation');}
  await p.keyboard.press(key);
  if(key==='3'){
   await p.waitForSelector('.memo-explanation');
   if(index!==3)throw Error('forgot skipped explanation');
   if(await p.locator('.memo-heading h2').innerText()!=='want to')throw Error('forgot did not reveal answer');
   await p.keyboard.press('Space');
  }
  await p.waitForSelector('.memo-writing input');
 }
 if(saved.join(',')!=='clear,hard,forgot'||index!==4)throw Error(JSON.stringify({saved,index}));
 await p.locator('.nav').nth(1).click();await p.locator('.nav').first().click();await p.waitForSelector('.memo-writing input');
 await p.locator('.memo-toolbar button').first().click();await p.waitForSelector('.memo-explanation');if(!await p.locator('.study-mode').count())throw Error('back navigated away');await p.keyboard.press('Space');await p.waitForSelector('.memo-writing input');if(saved.length!==3)throw Error('review regraded');
 console.log('PASS: automatic entry, 1/2/3 save then advance, navigation resumes question');await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
