import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';

async function getJson(path:string,body?:unknown){const r=await learningFetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json().catch(()=>null);if(!r.ok)throw Error(typeof d?.detail==='string'?d.detail:`请求失败（${r.status}）`);return d;}
export function UserCourseStudy({speak,openDictionary}:{speak:(text:string)=>void;openDictionary:()=>void}){
 const [item,setItem]=useState<any>(null),[answer,setAnswer]=useState(''),[revealed,setRevealed]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[hasCourses,setHasCourses]=useState<boolean|null>(null);
 async function next(){setBusy(true);setError('');try{const d=await getJson('/api/user-courses/next');setItem(d);setAnswer('');setRevealed(null);if(d.kind==='done'){const courses=await getJson('/api/user-courses');setHasCourses(courses.length>0);}}catch(e){setError(e instanceof Error?e.message:'读取今日课程失败');}finally{setBusy(false);}}
 useEffect(()=>{void next();},[]);
 async function reveal(){if(!item?.item_id)return;setError('');try{setRevealed(await getJson('/api/user-courses/reveal/'+item.item_id));}catch(e){setError(e instanceof Error?e.message:'答案读取失败');}}
 async function rate(confidence:string){if(!answer.trim()||!item?.item_id)return;setBusy(true);setError('');try{const d=await getJson('/api/user-courses/answer',{item_id:item.item_id,answer,confidence});setItem(d.next||{kind:'done',message:'今天的自定课程内容已完成；未完成项会在后续继续。'});setAnswer('');setRevealed(null);if(!d.next){const courses=await getJson('/api/user-courses');setHasCourses(courses.length>0);}}catch(e){setError(e instanceof Error?e.message:'保存自评失败');}finally{setBusy(false);}}
 const typeLabel:Record<string,string>={word:'单词',focus:'本组重点',sentence:'必背句',transfer:'迁移练习'};
 return <section className="panel user-study-page" aria-live="polite">
  {error&&<p role="alert">{error}</p>}
  {!item&&!error&&<p>正在读取今日课程…</p>}
  {item?.kind==='done'&&<><h2>{hasCourses===false?'先导入你的课程':'今日内容已完成'}</h2><p>{hasCourses===false?'这里会按你提供的课程与自评规则安排每日学习。':'未完成的项目会保留，之后继续；到期项目会优先出现。'}</p><div className="user-study-actions">{hasCourses===false?<button onClick={openDictionary}>前往我的词典导入课程</button>:<button disabled={busy} onClick={()=>void next()}>刷新今日安排</button>}</div></>}
  {item&&item.kind!=='done'&&<article className="user-course-card"><small>第 {item.group} 组 · {typeLabel[item.kind]||'课程内容'}</small><h2>{item.prompt}</h2><label className="user-answer-label">英文答案<input aria-label="英文答案" autoComplete="off" value={answer} onChange={e=>setAnswer(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.nativeEvent.isComposing)void reveal();}} placeholder="输入英文答案"/></label><div className="user-study-actions"><button disabled={busy||!answer.trim()} onClick={()=>void reveal()}>查看可接受答案</button>{revealed&&<button type="button" onClick={()=>speak(revealed.answer)}>播放发音</button>}</div>
  {revealed&&<><div className="user-course-answer"><strong>可接受答案：{revealed.accepted_answers.join(' / ')}</strong><small>忽略大小写和多余空格；拼写与词形须匹配。</small></div><p>请按自己的判断选择：</p><div className="user-course-ratings">{(item.kind==='word'?[['fuzzy','模糊'],['remember','记住'],['familiar','熟悉']]:[['fuzzy','模糊'],['remember','记住'],['transfer','迁移']]).map(([value,label])=><button key={value} disabled={busy} onClick={()=>void rate(value)}>{label}</button>)}</div></>}
  </article>}
 </section>;
}
