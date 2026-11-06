import {peekRead} from './readCache';
import {isTestMode} from './testMode';
import {TeachingRoute} from './TeachingRoute';
import {DailyOverview} from './DailyOverview';
import {CourseSelection} from './CourseSelection';
import {DailyLimits} from './DailyLimits';
import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
export function Plan(_props:{start:()=>void}){
 const [data,setData]=useState<any>(()=>peekRead((isTestMode()?'test:':'real:')+'/api/plan?compact=true')),[error,setError]=useState('');
 useEffect(()=>{let active=true;const load=()=>learningFetch('/api/plan?compact=true').then(r=>{if(!r.ok)throw Error('计划读取失败');return r.json();}).then(d=>{if(active){setData(d);setError('');}}).catch(e=>{if(active)setError(e.message);});void load();window.addEventListener('settings-status',load);return()=>{active=false;window.removeEventListener('settings-status',load);};},[]);
 return <section className="panel plan-page">{error&&<p role="alert">{error}</p>}<header className="plan-today"><DailyLimits showProgress/></header>
 <DailyOverview planning/>
 {data&&<section className="plan-adjust"><CourseSelection courses={data.curriculum||[]}/></section>}
 {data?<TeachingRoute route={data.route}/>:!error&&<p>读取课程路线…</p>}</section>;
}