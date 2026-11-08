import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
export function UserCourseProfile(){
 const [data,setData]=useState<any>(null),[error,setError]=useState('');
 useEffect(()=>{let active=true;learningFetch('/api/user-courses/summary').then(r=>{if(!r.ok)throw Error('自定课程记录读取失败');return r.json();}).then(d=>{if(active){setData(d);setError('');}}).catch(e=>{if(active)setError(e instanceof Error?e.message:'读取失败');});return()=>{active=false;};},[]);
 const labels:Record<string,string>={new:'未练',learning:'当天复现中',relearning:'次日重练',fuzzy:'模糊',remember:'记住',familiar:'熟悉',transfer:'迁移'};
 return <section className="panel user-plan"><h2>学习记录</h2>{error&&<p role="alert">{error}</p>}{!data&&!error&&<p>读取记录…</p>}{data&&<><p>这里只汇总自定课程与用户点击的自评，不推断掌握程度。</p><div className="user-plan-counts"><div><strong>{data.total}</strong><span>课程内容</span></div><div><strong>{data.today_done}</strong><span>今日自评次数</span></div><div><strong>{data.due}</strong><span>今日待学/复习</span></div><div><strong>{data.overdue}</strong><span>此前到期</span></div></div><h3>当前自评状态</h3>{Object.entries(data.states as Record<string,number>).map(([key,count])=><article className="user-plan-course" key={key}><strong>{labels[key]||key}</strong><span>{count} 项</span></article>)}</>}</section>;
}
