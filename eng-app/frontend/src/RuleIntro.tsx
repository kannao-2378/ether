import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
export function RuleIntro({id}:{id:string}){
 const rule=id.startsWith('want-to')||id.includes('compose-want-to')?'want-to':id.startsWith('enjoy-doing')||id.includes('compose-enjoy-doing')?'enjoy-doing':null;
 const [data,setData]=useState<any>(null);
 useEffect(()=>{let active=true;setData(null);if(rule)learningFetch('/api/rules/'+rule+'/read',{method:'POST'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(active)setData(d);}).catch(()=>{});return()=>{active=false;};},[rule]);
 if(!data)return null;
 return <section className="memory-summary rule-intro"><h3>{data.title}</h3>{data.points.map((point:string)=><p key={point}>{point}</p>)}<small>{data.state} · 独立运用 {data.independent_uses} 次</small><p><a href={data.sources[0]} target="_blank" rel="noreferrer">规则依据：British Council</a></p></section>;
}
