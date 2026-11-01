const { chromium } = require('C:/Users/X/AppData/Local/OpenAI/Codex/runtimes/cua_node/5c41f77a7900391c/bin/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage();
 let submissions=0,reveals=0;
 await page.addInitScript(()=>{
  localStorage.setItem('speech-auto','off');
  window.spoken=[];
  window.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
  Object.defineProperty(window,'speechSynthesis',{value:{getVoices:()=>[{name:'Microsoft Zira',voiceURI:'zira',lang:'en-US',localService:true}],addEventListener(){},removeEventListener(){},cancel(){},resume(){},speak(u){if(u.text.trim())window.spoken.push(u.text);}}});
 });
 await page.route('**/api/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  let data={};
  if(path.endsWith('/dashboard'))data={items:[{id:'test',answer:'want to',introduced:1,streak:0}],history:[],due:1,today_count:0};
  if(path.endsWith('/next'))data={kind:'recall',question_id:'q-test',id:'test',prompt:'Recall test'};
  if(path.includes('/reveal/')){reveals++;data={answer:'want to',explanation:'Explanation'};}
  if(path.endsWith('/answers'))submissions++;
  await route.fulfill({json:data});
 });
 await page.goto('http://127.0.0.1:5173');
 await page.locator('.welcome .primary').click();
 const input=page.locator('.exercise > input');await input.fill('want to');
 await input.press('Enter');await page.waitForTimeout(200);
 if(submissions!==0||reveals!==1||await page.locator('.feedback').count()!==0)throw Error('Enter caused extra UI/submission operation');
 if(await page.evaluate(()=>window.spoken.length)!==1)throw Error('Enter count: '+JSON.stringify(await page.evaluate(()=>window.spoken)));
 await page.locator('.rating.clear').focus();await page.keyboard.press('Enter');await page.waitForTimeout(200);
 if(submissions!==0||await page.evaluate(()=>window.spoken.length)!==2)throw Error('Focused button triggered extra action');
 console.log('PASS: Enter speaks once, does not submit or show answer; focused button also safe.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});

