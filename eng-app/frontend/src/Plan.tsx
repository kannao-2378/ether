import {CourseUnit} from './CourseUnit';
import {CourseSelection} from './CourseSelection';
import {CurriculumOutline} from './CurriculumOutline';
import {DailyLimits} from './DailyLimits';
import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
export function Plan({start}:{start:()=>void}){
 const [data,setData]=useState<any>(null),[error,setError]=useState('');
 useEffect(()=>{const load=()=>learningFetch('/api/plan').then(r=>{if(!r.ok)throw Error('计划读取失败');return r.json();}).then(setData).catch(e=>setError(e.message));void load();window.addEventListener('settings-status',load);return()=>window.removeEventListener('settings-status',load);},[]);
 return <section className="panel"><DailyLimits/>{error&&<p role="alert">{error}</p>}{data&&<>
 <CourseSelection courses={data.curriculum||[]}/>
 {data.packages?.map((pack:any)=><div className="course-pack-summary" key={pack.id}><strong>{pack.expression_count.toLocaleString()} 个表达</strong><span>{pack.sentence_count.toLocaleString()} 个双语例句 · {pack.word_count.toLocaleString()} 项词汇</span></div>)}
 <CurriculumOutline courses={data.curriculum||[]}/>
 {data.curriculum?.map((course:any)=><details className="curriculum" key={course.id} open={course.id==='foundation'}><summary><h3>{course.title}</h3><small>{course.units.length} / {course.total}</small></summary><p>{course.goal}</p>{course.units.map((u:any)=><CourseUnit key={u.id} unit={u}/>)}</details>)}
 <div className="stats"><div><small>到期</small><strong>{data.cross_day_due} <em>组</em></strong></div><div><small>巩固</small><strong>{data.same_day_practice} <em>组</em></strong></div><div><small>已练</small><strong>{data.today_count} <em>次</em></strong></div></div><p>今日安排：新学 {data.new_admitted} · 复习 {data.review_admitted}</p><button className="primary" onClick={start}>进入今日学习</button><h3>规则进度</h3>{data.rules.map((r:any)=><div className="row" key={r.id}><div><strong>{r.title}</strong><small>{r.state}</small></div><span>独立运用 {r.independent_uses} 次</span></div>)}<h3>需要巩固</h3>{data.weak.length?data.weak.map((i:any)=><div className="row" key={i.id}><span>{i.answer} · {i.prompt}</span><span>{i.familiarity}</span></div>):<p>暂无待巩固内容。</p>}</>}</section>;
}
