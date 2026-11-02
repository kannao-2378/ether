import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
const ratings:Record<string,string>={clear:'认识',hard:'模糊',forgot:'忘记'};
const states:Record<string,string>={completed:'今日完成',practiced:'已练 · 待巩固',started:'已开始',waiting:'按课程顺序等待'};
export function DailyOverview({planning=false}:{planning?:boolean}){
 const [data,setData]=useState<any>(null),[day,setDay]=useState(''),[error,setError]=useState('');
 useEffect(()=>{let active=true;const load=()=>{setError('');learningFetch('/api/daily-activity?planning='+planning+(day?'&day='+day:'')).then(r=>{if(!r.ok)throw Error('当天记录读取失败');return r.json();}).then(d=>{if(active){setData(d);}}).catch(e=>{if(active)setError(e.message);});};load();window.addEventListener('settings-status',load);window.addEventListener('focus-updated',load);return()=>{active=false;window.removeEventListener('settings-status',load);window.removeEventListener('focus-updated',load);};},[day,planning]);
 async function cancel(id:string){try{const r=await learningFetch('/api/focus-cancel/'+id,{method:'POST'});if(!r.ok)throw Error('取消失败，请刷新后重试');window.dispatchEvent(new Event('focus-updated'));}catch(e){setError((e as Error).message);}}
 const list=(rows:any[],label:string)=><details className="daily-list" open><summary>{label} · {rows.length}</summary>{rows.length?rows.map((r:any)=><div className="daily-entry" key={r.id}><span>{r.title}</span>{r.status&&<small>{states[r.status]}</small>}</div>):<p>暂无</p>}</details>;
 return <section className="daily-overview"><div className="daily-title"><h3>{planning?'今日安排':'当天学习'}</h3>{!planning&&<input aria-label="学习日期" type="date" value={day||data?.date||''} max={new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date())} onChange={e=>setDay(e.target.value)}/>}</div>{error&&<p role="alert">{error}</p>}{!data&&!error&&<p>读取中…</p>}{data&&<>
 <div className="daily-numbers"><span>新学 <b>{planning?data.new:data.studied_new}</b> 组</span><span>复习 <b>{planning?data.review:data.studied_review}</b> 组</span>{data.special>0&&<span>专项 <b>{data.special}</b> 组</span>}<span>答题 <b>{data.attempts}</b> 次</span></div>
 {planning?<>{data.focus?.length>0&&<details open className="daily-list"><summary>专项训练 · {data.focus.length}</summary>{data.focus.map((f:any)=><div className="daily-entry" key={f.id}><span>{f.title}</span><small>{({pending:'排队中',active:'训练中',completed:'已完成'} as Record<string,string>)[f.status]}</small>{f.status!=='completed'&&<button onClick={()=>void cancel(f.id)}>取消</button>}</div>)}</details>}{list(data.groups.filter((g:any)=>g.kind!=='special'),'已开始')}{list(data.preview_review,'待复习')}{list(data.preview_new,'预计新学')}<small>新课按课程目录推进，同时最多 3 组；复习按记忆安排穿插。{data.review_waiting>data.preview_review.length&&`另有 ${data.review_waiting-data.preview_review.length} 组到期内容待安排。`}</small></>:<>
 <p className="daily-result">共练习 {data.studied_groups} 组 · {data.items.length} 项内容</p>
 <div className="daily-numbers">{Object.entries({word:'单词',collocation:'搭配',phrase:'短语',sentence:'句子',rule:'规则'}).filter(([k])=>k!=='rule'||data.type_counts[k]>0).map(([k,label])=><span key={k}>{label} <b>{data.type_counts[k]||0}</b></span>)}</div>
 <small>同一项反复练习只计一次。组是任务单位，一组可包含单词、搭配和句子。</small>
 <p className="daily-result">独立通过 {data.independent} 次</p><div className="daily-numbers">{Object.entries(data.feedback).map(([r,n])=><span key={r}>{ratings[r]} <b>{String(n)}</b></span>)}</div>

 </>}
 </>}</section>;
}
