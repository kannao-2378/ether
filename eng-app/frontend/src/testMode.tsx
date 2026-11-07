import {cachedRead,clearReadCache,invalidateReadCache} from './readCache';
import {useEffect,useState} from 'react';
import {apiUrl,csrfHeaders,isPrivateMode} from './apiBase';
export const isTestMode=()=>!isPrivateMode()&&sessionStorage.getItem('learning-test')==='1';
// Study actions only change study-domain data; dictionary/settings caches survive them.
const STUDY_DOMAINS=['/api/dashboard','/api/plan','/api/daily-activity','/api/profile'];
const STUDY_POSTS=new Set(['/api/next','/api/answers','/api/feedback','/api/daily-extra','/api/context/new-round']);
const STUDY_POST_PREFIXES=['/api/introduce/','/api/reveal/','/api/challenge/','/api/test/'];
export function learningFetch(input:string,init:RequestInit={}){
 const headers=new Headers(init.headers);if(isTestMode())headers.set('X-Learning-Test','1');
 if(!['GET','HEAD'].includes((init.method||'GET').toUpperCase()))for(const [k,v] of Object.entries(csrfHeaders()))headers.set(k,v);
 const method=(init.method||'GET').toUpperCase();
 const path=input.split('?')[0];
 const studyPost=STUDY_POSTS.has(path)||STUDY_POST_PREFIXES.some(p=>path.startsWith(p));
 const load=()=>fetch(apiUrl(input),{...init,headers,credentials:'same-origin'}).then(r=>{if(r.status===401&&!input.includes('/auth/'))window.dispatchEvent(new Event('login-required'));if(r.ok&&method!=='GET'&&method!=='HEAD'&&!['/api/check-word','/api/check'].includes(path)){if(studyPost){const prefix=isTestMode()?'test:':'real:';invalidateReadCache(STUDY_DOMAINS.map(d=>prefix+d));}else clearReadCache();}return r;});
 if(method==='GET'&&!init.signal){const ttl=path==='/api/settings'?5000:/^\/api\/(dictionary|plan|daily-activity|profile)/.test(path)?300000:0;if(ttl)return cachedRead((isTestMode()?'test:':'real:')+input,ttl,load);}
 return load();
}
export function TestModeSettings(){
 if(isPrivateMode())return null;
 const active=isTestMode();
 const [time,setTime]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[starter,setStarter]=useState(false);
 useEffect(()=>{if(active)learningFetch('/api/test/status').then(r=>r.json()).then(s=>{setTime(new Date(s.time).toLocaleString());setStarter(Boolean(s.starter_course));}).catch(()=>setError('无法连接测试服务'));},[]);
 async function action(name:string,data={}){setBusy(true);setError('');try{const r=await learningFetch('/api/test/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok){const body=await r.json().catch(()=>({}));throw Error(body.detail||'操作失败，请重试');}if(name==='unlock'){window.dispatchEvent(new Event('enter-next-stage'));setBusy(false);return;}location.reload();}catch(e){setError(String(e));setBusy(false);}}
 return <div className="test-mode-settings"><h2>独立测试模式</h2><p>测试数据与真实学习数据分开。模拟日期不修改电脑时间；切换后页面会刷新。</p><button onClick={()=>{sessionStorage.setItem('learning-test',active?'0':'1');location.reload();}}>{active?'退出测试，返回真实学习':'进入测试模式'}</button>{active&&<><p>模拟时间：{time}</p><button disabled={busy} onClick={()=>action(starter?'starter-exit':'starter-course')}>{starter?'退出当前课程试学':'启用起步课程试学'}</button>{!starter&&<button disabled={busy} onClick={()=>action('mainline-course')}>启用完整主线试学 · 148课题</button>}<small>首次启用前需清空测试进度；试学复用正常书写、反馈和复习流程。</small><div className="actions">{[[1,'解锁搭配'],[2,'解锁短句'],[3,'解锁句子'],[4,'解锁中文情境']].map(([stage,label])=><button disabled={busy||starter} key={stage} onClick={()=>action('unlock',{stage})}>{label}</button>)}</div><p>阶段预览不与课程试学混用。“短句”阶段练习动作短语。</p><button disabled={busy||starter} onClick={()=>action('transfer-pilot')}>启用 want to 迁移备课试点</button><button disabled={busy} onClick={()=>action('reset')}>清空测试进度</button></>}{error&&<p role="alert">{error}</p>}</div>;
}
