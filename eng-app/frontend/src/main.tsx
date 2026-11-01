import {AuthGate} from './AuthGate';
import {useViewport} from './useViewport';
import {requestId} from './requestId';
import {LearningProfile} from './LearningProfile';
import {Plan} from './Plan';
import {useKeybindings,eventKey} from './keybindings';
import {Dictionary} from './Dictionary';
import {Lesson} from './Lesson';
import {learningFetch,isTestMode} from './testMode';
import React, {useEffect,useState,useRef} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import {Study} from './Study';
import {Settings,useTheme} from './settings';
import {useLocalSpeech} from './speech';
const BASE='/api';
async function api(path:string,data?:unknown){const r=await learningFetch(BASE+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok){const detail=await r.json().catch(()=>null);throw Error(typeof detail?.detail==='string'?detail.detail:`请求失败（${r.status}），请重试。`);}return r.json();}
function App({onLogout}:{onLogout?:()=>void}){
 useViewport();
 const actionLock=useRef(false);
 const summaryRevision=useRef(0);
 const latestSummary=useRef<any>(null);
 const [keys]=useKeybindings();
 const [reviewSpelling,setReviewSpelling]=useState(false);
 const resumeDraft=useRef<any>(null);
 const [previousItems,setPreviousItems]=useState<any[]>([]);
 const [reviewIndex,setReviewIndex]=useState<number|null>(null);
 const [checked,setChecked]=useState<any>(null);
 const [checking,setChecking]=useState(false);
 const [checkError,setCheckError]=useState('');
 const [shake,setShake]=useState(0);
 const checkLock=useRef(false);
 const latestCheckValue=useRef('');
 const checkKey=useRef('');
 const composing=useRef(false);
 const [peek,setPeek]=useState(false);
 const speech=useLocalSpeech();
 const {theme,setTheme}=useTheme();
 const spokenQuestion=useRef('');
 const [page,setPage]=useState('今日学习'),[dashboard,setDashboard]=useState<any>(null),[q,setQ]=useState<any>(null),[answer,setAnswer]=useState(''),[confidence,setConfidence]=useState('clear'),[result,setResult]=useState<any>(null),[hint,setHint]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function refresh(){const d=await api('/dashboard');setDashboard({...d,...latestSummary.current});setPreviousItems(items=>items.length?items:[...d.history].reverse().map((a:any)=>({...d.items.find((i:any)=>i.id===a.knowledge_id),kind:'recall',question_id:a.question_id,confidence:a.confidence})));}
 async function refreshSummary(){const revision=++summaryRevision.current;try{const d=await api('/dashboard?summary_only=true');if(revision!==summaryRevision.current)return;latestSummary.current=d;setDashboard((previous:any)=>previous?{...previous,...d}:previous);}catch{/* Statistics must not block typing; retry on the next question. */}}
 useEffect(()=>{refresh().catch(()=>setError('连接不到学习服务，请检查网络后重试。'));},[]);
 async function act(fn:()=>Promise<void>){if(actionLock.current)return;actionLock.current=true;setBusy(true);setError('');try{await fn();}catch(e){setError(e instanceof Error?e.message:'操作失败');}finally{actionLock.current=false;setBusy(false);}}
 async function next(){if(q?.context_round_complete)await api('/context/new-round',{});const question=await api('/next',{});if(q?.question_id&&q.kind!=='done')setPreviousItems(items=>[...items,{...q,confidence}]);speech.stop();setReviewIndex(null);setChecked(null);setCheckError('');checkKey.current='';setPeek(false);setQ(question.kind==='done'?{...question,checked_at:Date.now()}:question);setAnswer('');setResult(null);setHint(null);setConfidence('clear');void refreshSummary();}
 useEffect(()=>{const enter=()=>{setPage('今日学习');void act(next);};window.addEventListener('enter-next-stage',enter);return()=>window.removeEventListener('enter-next-stage',enter);});
 function previous(){
  if(busy||checking)return;speech.stop();setPeek(false);setError('');
  if(reviewIndex===null){if(!previousItems.length)return;resumeDraft.current={answer,checked};setReviewIndex(previousItems.length-1);setReviewSpelling(false);setChecked(null);}
  else if(!reviewSpelling){setReviewSpelling(true);setAnswer('');setChecked(null);checkKey.current='';}
  else if(reviewIndex>0){setReviewIndex(reviewIndex-1);setReviewSpelling(false);setChecked(null);}
 }
 function reviewNext(){speech.stop();setReviewSpelling(false);setChecked(null);if(reviewIndex===null||reviewIndex>=previousItems.length-1){setReviewIndex(null);setAnswer(resumeDraft.current?.answer||'');setChecked(resumeDraft.current?.checked||null);}else setReviewIndex(reviewIndex+1);}
 useEffect(()=>{if(page==='今日学习'&&(!q||q.kind==='done'))void act(next);},[page]);
 async function submitAnswer(value:string){
  if(checking||busy)return;
  if(reviewIndex!==null){
   if(reviewSpelling&&!checked?.correct)return;
   await act(async()=>{await api('/feedback',{question_id:previousItems[reviewIndex].question_id,confidence:value});setPreviousItems(items=>items.map((item,index)=>index===reviewIndex?{...item,confidence:value}:item));reviewNext();});return;
  }
  if(q?.kind==='learn'){await act(async()=>{await api('/introduce/'+q.id,{});await next();});return;}
  if(!checked?.correct)return;
  setConfidence(value);
  await act(async()=>{const saved=await api('/answers',{question_id:q.question_id,answer,confidence:value});if(saved.confidence!==value)await api('/feedback',{question_id:q.question_id,confidence:value});const completed={...q,confidence:value};setPreviousItems(items=>[...items.filter(i=>i.question_id!==q.question_id),completed]);const question=await api('/next',{});speech.stop();setQ(question.kind==='done'?{...question,checked_at:Date.now()}:question);setAnswer('');setChecked(null);setResult(null);setHint(null);checkKey.current='';void refreshSummary();});
 }
 async function startChallenge(){
  if(!q?.id||reviewIndex!==null)return;
  await act(async()=>{const question=await api('/challenge/'+q.id,{});speech.stop();setQ(question.kind==='done'?{...question,checked_at:Date.now()}:question);setAnswer('');setChecked(null);setHint(null);setResult(null);setPeek(false);checkKey.current='';void refreshSummary();});
 }
 async function skipForTest(){
  if(!isTestMode()||!q?.question_id||reviewIndex!==null)return;
  await act(async()=>{await api('/test/skip-question/'+q.question_id,{});await next();});
 }
 async function continueLearning(){await act(async()=>{if(q?.kind==='learn')await api('/introduce/'+q.id,{});await next();});}
 async function revealAnswer(){
  if(q?.kind!=='recall'||result||hint)return;
  await act(async()=>{const revealed=await api('/reveal/'+q.question_id,{});setHint(revealed);});
 }
 function pronounce(){
  const active=reviewIndex===null?q:previousItems[reviewIndex];
  if(!active)return;
  const text=checked?.answer||active.answer||dashboard?.items.find((i:any)=>i.id===active.id)?.answer||'';
  if(!text){setError('当前题目的发音内容尚未加载，请重新连接后重试。');return;}
  // Keep playback inside the original tap, rather than after a network await.
  if(active.kind==='recall'&&!checked?.correct&&active.question_id)void api('/reveal/'+active.question_id,{}).catch(e=>setError(e instanceof Error?e.message:'提示记录保存失败，请重试。'));
  speech.speak(text);
 }

 useEffect(()=>{
  let controlOnly=false;
  function keydown(e:KeyboardEvent){
   if(page!=='今日学习'||e.isComposing)return;
   const activeItem=reviewIndex===null?q:previousItems[reviewIndex];
   const transferStage=dashboard?.items.find((i:any)=>i.id===activeItem?.id)?.stage===4;
   const writing=reviewIndex===null?!checked?.correct:reviewSpelling&&!checked?.correct;
   const key=eventKey(e);
   if((e.target as HTMLElement).closest('select'))return;
   if(key===keys.peek){
    e.preventDefault();e.stopImmediatePropagation();
    if(!e.repeat&&!busy&&writing){setPeek(true);const target=activeItem?.question_id;if(target)void api('/reveal/'+target,{}).catch(e=>setError(e instanceof Error?e.message:'提示记录保存失败，请重试。'));}
    return;
   }
   if(key===(transferStage&&writing?keys.submit:keys.audio)||transferStage&&key===keys.contextAudio){
    e.preventDefault();e.stopImmediatePropagation();
    if(!e.repeat&&!busy&&!checking){if(transferStage&&writing&&key===keys.submit)void checkInput(answer);else if(reviewIndex!==null)speech.speak(dashboard?.items.find((i:any)=>i.id===activeItem?.id)?.answer||'');else pronounce();}
    return;
   }
   if(key===keys.familiar){e.preventDefault();e.stopImmediatePropagation();if(!e.repeat&&!busy&&reviewIndex===null)void startChallenge();return;}
   if(e.code==='Space'&&!(e.target instanceof HTMLInputElement)&&!(e.target instanceof HTMLTextAreaElement)){e.preventDefault();e.stopImmediatePropagation();return;}
   if(e.repeat||busy||e.ctrlKey||e.altKey||e.metaKey)return;
   if(!writing||q?.kind==='learn'){
    const values:Record<string,string>={[keys.clear]:'clear',[keys.hard]:'hard',[keys.forgot]:'forgot'};
    if(values[key]){e.preventDefault();e.stopImmediatePropagation();void submitAnswer(values[key]);}
   }
  }
  function keyup(e:KeyboardEvent){if(e.key===keys.peek||eventKey(e)===keys.peek)setPeek(false);if(page==='????'&&e.code==='Space'&&!(e.target instanceof HTMLInputElement)&&!(e.target instanceof HTMLTextAreaElement)){e.preventDefault();e.stopImmediatePropagation();}}
  function blur(){controlOnly=false;setPeek(false);}
  window.addEventListener('keydown',keydown,true);window.addEventListener('keyup',keyup,true);window.addEventListener('blur',blur);
  return()=>{window.removeEventListener('keydown',keydown,true);window.removeEventListener('keyup',keyup,true);window.removeEventListener('blur',blur);};
 });
 useEffect(()=>{
  speech.stop();
  if(page!=='今日学习')return;
  const text=q?.kind==='learn'?q.answer:hint?.answer;
  const token=`${q?.id}:${result?'result':hint?'hint':'learn'}`;
  if(text&&speech.auto&&speech.ready&&spokenQuestion.current!==token){spokenQuestion.current=token;speech.speak(text);}
 },[q?.id,q?.kind,page,!!result,!!hint,speech.auto,speech.ready]);
 async function checkInput(value:string,force=false){
  latestCheckValue.current=value;
  if(checkLock.current||result||checked?.correct||composing.current)return;
  const active=reviewIndex===null?q:previousItems[reviewIndex];
  const limit=active?.answer_length??dashboard?.items.find((i:any)=>i.id===active?.id)?.answer.length;
  const isTransfer=dashboard?.items.find((i:any)=>i.id===active?.id)?.stage===4;
  if(!value.trim()||(!force&&!isTransfer&&(!limit||value.trim().replace(/[.!?。！？]+$/,'').trim().length<limit)))return;
  const key=active.question_id+':'+value;
  if(checkKey.current===key)return;
  checkKey.current=key;checkLock.current=true;setChecking(true);setCheckError('');
  try{const r=await api('/check',{id:requestId(),question_id:active.question_id,answer:value});if(latestCheckValue.current!==value)return;checkKey.current=key;setChecked(r);if(!r.correct)setShake(v=>v+1);else if(speech.auto)speech.speak(r.answer);}
  catch{checkKey.current='';setCheckError('检查失败，点击重试，答案尚未判定。');}
  finally{checkLock.current=false;setChecking(false);if(latestCheckValue.current!==value)void checkInput(latestCheckValue.current);}
 }
 const total=dashboard?.items.length??0;
 const introduced=dashboard?.items.filter((i:any)=>i.introduced).length??0;
 const current=dashboard?.items.find((i:any)=>i.id===q?.id);
 return <div className={page==='今日学习'?'shell study-mode':'shell'}><nav className="mobile-pages" aria-label="页面导航">{['今日学习','学习计划','我的词典','学习档案','设置'].map(p=><button key={p} aria-current={page===p?'page':undefined} onClick={()=>setPage(p)}>{p}</button>)}</nav><aside><div className="brand">循序<span>ENGLISH LEARNING</span></div><div className="label">个人学习空间</div>{['今日学习','学习计划','我的词典','学习档案','设置'].map(p=><button key={p} className={page===p?'nav active':'nav'} onClick={()=>setPage(p)}>{p}<span>›</span></button>)}{onLogout&&<button className="nav logout" onClick={onLogout}>退出登录</button>}<div className="aside-bottom"><i/> 学习进度 · 自动保存<small>从搭配开始，慢慢说出自己的话。</small></div></aside><main>{isTestMode()&&<div className="test-mode-banner">独立测试模式 · 使用测试数据库 · 可在设置中模拟日期或退出</div>}<header><div><h1>{page}</h1></div><span className="badge">阶段 01 · 基础搭配</span></header>{error&&<div role="alert" className="error">{error}<button onClick={()=>act(refresh)}>重新连接</button></div>}
 {page==='今日学习'?<><Study peekStart={()=>{if(busy||checking)return;setPeek(true);const target=(reviewIndex===null?q:previousItems[reviewIndex])?.question_id;if(target)void api('/reveal/'+target,{}).catch(e=>setError(e instanceof Error?e.message:'提示记录保存失败，请重试。'));}} peekEnd={()=>setPeek(false)} speechMessage={speech.message} reviewCount={dashboard?.today_review??0} newCount={dashboard?.today_new??0} keys={keys} canChallenge={reviewIndex===null&&q?.kind==='learn'} challenge={()=>void startChallenge()} canSkip={isTestMode()&&reviewIndex===null&&q?.kind==='recall'&&!checked?.correct} skip={()=>void skipForTest()} previousDisabled={busy||checking||!previousItems.length} selectedFeedback={reviewIndex===null?null:previousItems[reviewIndex]?.confidence} reviewing={reviewIndex!==null} peek={peek} q={reviewIndex===null?q:{...dashboard?.items.find((i:any)=>i.id===previousItems[reviewIndex]?.id),...previousItems[reviewIndex],kind:reviewSpelling?'recall':'learn'}} current={reviewIndex===null?current:dashboard?.items.find((i:any)=>i.id===previousItems[reviewIndex]?.id)} introduced={introduced} total={total} crossDayDue={dashboard?.cross_day_due??0} sameDayPractice={dashboard?.same_day_practice??0} todayCount={dashboard?.today_count??0} answer={answer} checked={checked} hint={reviewIndex===null?hint:null} result={reviewIndex===null?result:null} busy={busy} checking={checking} checkError={checkError} shake={shake} speak={speech.speak} pronounce={pronounce} reveal={()=>void revealAnswer()} submit={submitAnswer} next={()=>reviewIndex!==null?reviewNext():void continueLearning()} back={previous} navigate={setPage} retry={()=>void checkInput(answer,true)} compositionStart={()=>{composing.current=true;}} compositionEnd={(e:any)=>{composing.current=false;if((reviewIndex===null?current:dashboard?.items.find((i:any)=>i.id===previousItems[reviewIndex]?.id))?.stage!==4)void checkInput(e.currentTarget.value);}} change={(e:any)=>{const value=e.target.value;setAnswer(value);setChecked(null);checkKey.current='';if((reviewIndex===null?current:dashboard?.items.find((i:any)=>i.id===previousItems[reviewIndex]?.id))?.stage!==4)void checkInput(value);}}/></>:page==='学习计划'?<Plan start={()=>setPage('今日学习')}/>:page==='我的词典'?<Dictionary speak={speech.speak}/>:page==='规则课程'?<Lesson speak={speech.speak}/>:page==='设置'?<Settings onLogout={onLogout} theme={theme} setTheme={setTheme} speech={speech.controls} back={()=>setPage('今日学习')}/>:<LearningProfile/>}
 </main></div>;
}
createRoot(document.getElementById('root')!).render(<AuthGate>{logout=><App onLogout={logout}/>}</AuthGate>);
