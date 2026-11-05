import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
const ratings:Record<string,string>={clear:'认识',hard:'模糊',forgot:'忘记'};
const states:Record<string,string>={completed:'今日完成',practiced:'已练 · 待巩固',started:'已开始',waiting:'等待',candidate:'候选',planned:'待安排'};
export function DailyOverview({planning=false}:{planning?:boolean}){
 const [tab,setTab]=useState('review'),[expanded,setExpanded]=useState(false);
 const [data,setData]=useState<any>(null),[day,setDay]=useState(''),[error,setError]=useState('');
 useEffect(()=>{let active=true;const load=()=>{setError('');learningFetch('/api/daily-activity?planning='+planning+(day?'&day='+day:'')).then(r=>{if(!r.ok)throw Error('当天记录读取失败');return r.json();}).then(d=>{if(active){setData(d);}}).catch(e=>{if(active)setError(e.message);});};load();window.addEventListener('settings-status',load);window.addEventListener('focus-updated',load);return()=>{active=false;window.removeEventListener('settings-status',load);window.removeEventListener('focus-updated',load);};},[day,planning]);
 const plannedRows=(kind:string)=>{const booked=(data.groups||[]).filter((g:any)=>g.kind===kind);const seen=new Set(booked.map((g:any)=>g.id));const preview=kind==='new'?data.preview_new:data.preview_review;return [...booked,...(preview||[]).filter((g:any)=>!seen.has(g.id)).map((g:any)=>({...g,status:kind==='new'?'candidate':'planned'}))];};
 const list=(rows:any[],label:string,open=true)=><details className="daily-list" open={open}><summary>{label} · {rows.length}</summary><div className="plan-item-grid">{rows.length?rows.slice(0,expanded?rows.length:10).map((r:any)=><div className="daily-entry" key={r.id}><span>{r.title}</span>{r.status&&<small>{states[r.status]}</small>}</div>):<p>暂无已安排内容</p>}</div>{rows.length>10&&<button className="plan-expand" onClick={()=>setExpanded(!expanded)}>{expanded?'收起':'展开全部 '+rows.length+' 项'}</button>}</details>;
 return <section className="daily-overview"><div className="daily-title"><h3>{planning?'今日安排':'当天学习'}</h3>{!planning&&<input aria-label="学习日期" type="date" value={day||data?.date||''} max={new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date())} onChange={e=>setDay(e.target.value)}/>}</div>{error&&<p role="alert">{error}</p>}{!data&&!error&&<p>读取中…</p>}{data&&<>
 <div className="daily-numbers"><span>新学 <b>{planning?data.new:data.studied_new}</b> 组</span><span>复习 <b>{planning?data.review:data.studied_review}</b> 组</span>{data.special>0&&<span>专项 <b>{data.special}</b> 组</span>}<span>答题 <b>{data.attempts}</b> 次</span></div>
 {planning?<><div className="plan-tabs" aria-label="今日任务分类">{[['review','复习'],['new','新学']].map(([key,label])=><button key={key} aria-pressed={tab===key} onClick={()=>{setTab(key);setExpanded(false);}}>{label} <small>{key==='candidate'?(data.preview_new||[]).length:key==='review'?plannedRows('review').length:(data.groups||[]).filter((g:any)=>g.kind===key).length}</small></button>)}</div>{list(plannedRows(tab).filter((r:any)=>r.status!=='candidate'),tab==='review'?'复习清单':'新学清单')}{tab==='new'&&list(plannedRows('new').filter((r:any)=>r.status==='candidate'),'候选新课',false)}<small>列出的是学习组名称；一组可能包含单词、搭配和句子。候选新课按大纲和掌握情况加入，不代表今天一定出题。{data.review_waiting>data.preview_review.length&&`另有 ${data.review_waiting-data.preview_review.length} 组到期内容待安排。`}</small></>:<>
 <p className="daily-result">共练习 {data.studied_groups} 组 · {data.items.length} 项内容</p>
 <div className="daily-numbers">{Object.entries({word:'单词',collocation:'搭配',phrase:'短语',sentence:'句子',rule:'规则'}).filter(([k])=>k!=='rule'||data.type_counts[k]>0).map(([k,label])=><span key={k}>{label} <b>{data.type_counts[k]||0}</b></span>)}</div>
 <small>同一项反复练习只计一次。组是任务单位，一组可包含单词、搭配和句子。</small>
 <p className="daily-result">独立通过 {data.independent} 次</p><div className="daily-numbers">{Object.entries(data.feedback).map(([r,n])=><span key={r}>{ratings[r]} <b>{String(n)}</b></span>)}</div>

 </>}
 </>}</section>;
}
