import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
const ratings:Record<string,string>={clear:'认识',hard:'模糊',forgot:'忘记'};
const states:Record<string,string>={completed:'今日完成',practiced:'已练 · 待巩固',started:'已开始'};
export function DailyOverview({planning=false}:{planning?:boolean}){
 const [data,setData]=useState<any>(null),[day,setDay]=useState(''),[error,setError]=useState(''),[page,setPage]=useState(1);
 useEffect(()=>{let active=true;const load=()=>{setError('');learningFetch('/api/daily-activity?planning='+planning+(day?'&day='+day:'')).then(r=>{if(!r.ok)throw Error('当天记录读取失败');return r.json();}).then(d=>{if(active){setData(d);setPage(1);}}).catch(e=>{if(active)setError(e.message);});};load();window.addEventListener('settings-status',load);return()=>{active=false;window.removeEventListener('settings-status',load);};},[day,planning]);
 const list=(rows:any[],label:string)=><details className="daily-list" open><summary>{label} · {rows.length}</summary>{rows.length?rows.map((r:any)=><div className="daily-entry" key={r.id}><span>{r.title}</span>{r.status&&<small>{states[r.status]}</small>}</div>):<p>暂无</p>}</details>;
 return <section className="daily-overview"><div className="daily-title"><h3>{planning?'今日安排':'当天学习'}</h3>{!planning&&<input aria-label="学习日期" type="date" value={day||data?.date||''} max={new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date())} onChange={e=>setDay(e.target.value)}/>}</div>{error&&<p role="alert">{error}</p>}{!data&&!error&&<p>读取中…</p>}{data&&<>
 <div className="daily-numbers"><span>新学 <b>{data.new}</b> 组／项</span><span>复习 <b>{data.review}</b> 组／项</span><span>答题 <b>{data.attempts}</b> 次</span></div>
 {planning?<>{list(data.groups,'已开始')}{list(data.preview_review,'待复习')}{list(data.preview_new,'预计新学')}<small>预计清单会随学习结果调整；已开始的内容优先巩固。{data.review_waiting>data.preview_review.length&&`另有 ${data.review_waiting-data.preview_review.length} 组到期内容待安排。`}</small></>:<>
 <p className="daily-result">涉及 {data.items.length} 项 · 独立通过 {data.independent} 次</p><div className="daily-numbers">{Object.entries(data.feedback).map(([r,n])=><span key={r}>{ratings[r]} <b>{String(n)}</b></span>)}</div>
 {!data.items.length?<p>当天暂无答题记录。</p>:<><div className="daily-entry daily-columns"><small>练习内容</small><small>次数 · 最后反馈</small></div>{data.items.slice((page-1)*20,page*20).map((r:any)=><div className="daily-entry" key={r.id}><div><strong>{r.english}</strong><small>{r.chinese}</small></div><span>{r.attempts} · {ratings[r.feedback]}</span></div>)}{data.items.length>20&&<div className="actions"><button disabled={page===1} onClick={()=>setPage(page-1)}>上一页</button><small>{page} / {Math.ceil(data.items.length/20)}</small><button disabled={page*20>=data.items.length} onClick={()=>setPage(page+1)}>下一页</button></div>}</>}
 </>}
 </>}</section>;
}
