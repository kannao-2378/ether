import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
export function UserCoursePlan({start}:{start:()=>void}){
 const [data,setData]=useState<any>(null),[error,setError]=useState('');
 useEffect(()=>{let active=true;learningFetch('/api/user-courses/summary').then(r=>{if(!r.ok)throw Error('自定课程计划读取失败');return r.json();}).then(d=>{if(active){setData(d);setError('');}}).catch(e=>{if(active)setError(e instanceof Error?e.message:'读取失败');});return()=>{active=false;};},[]);
 return <section className="panel user-plan"><h2>自定课程计划</h2>{error&&<p role="alert">{error}</p>}{!data&&!error&&<p>读取计划…</p>}{data&&<><p>{data.day} · 所有到期和未学内容按组序进入今日队列。</p><div className="user-plan-counts"><div><strong>{data.due}</strong><span>今日待学/复习</span></div><div><strong>{data.overdue}</strong><span>此前到期</span></div><div><strong>{data.today_done}</strong><span>今日已完成</span></div><div><strong>{data.total}</strong><span>课程内容</span></div></div><h3>已导入课程</h3>{data.courses.length?data.courses.map((c:any)=><article className="user-plan-course" key={c.id}><strong>{c.title}</strong><small>导入于 {new Date(c.created_at).toLocaleDateString()}</small></article>):<p>还没有课程。请到“我的词典”导入你的课程 JSON。</p>}<button onClick={start}>{data.courses.length?'开始今日学习':'今日学习'}</button></>}</section>;
}
