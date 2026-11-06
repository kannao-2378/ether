import {learningFetch} from './testMode';
import {useEffect,useState} from 'react';
import {useSharedSetting} from './sharedSetting';
export function DailyLimits({showProgress=false}:{showProgress?:boolean}){
 const [progress,setProgress]=useState<any>(null);
 useEffect(()=>{if(!showProgress)return;let active=true;learningFetch('/api/daily-activity').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(active)setProgress(d);}).catch(()=>{});return()=>{active=false;};},[showProgress]);
 const [message,setMessage]=useState('');
 useEffect(()=>{const show=(e:Event)=>setMessage((e as CustomEvent).detail);window.addEventListener('settings-status',show);return()=>window.removeEventListener('settings-status',show);},[]);
 const [review,setReview]=useSharedSetting('daily-review-limit',30);
 const [fresh,setFresh]=useSharedSetting('daily-new-limit',10);
 return <>{message&&<p role="status">{message}</p>}<div className="daily-limits" title="按表达组或独立单词计数；组内单词、搭配、句子和变式不重复扣名额；修改后自动保存"><span className="daily-limits-title">每日</span><label>复习 {showProgress&&<small>今日已学 {progress?progress.studied_review:"—"} /</small>}<input key={'r'+review} type="number" defaultValue={review} min={0} max={300} onBlur={e=>{const n=Number(e.target.value);if(Number.isInteger(n)&&n>=0&&n<=300&&n!==review)setReview(n);}}/> 组／项 / 天</label><label>新学 {showProgress&&<small>今日已学 {progress?progress.studied_new:"—"} /</small>}<input key={'n'+fresh} type="number" defaultValue={fresh} min={0} max={300} onBlur={e=>{const n=Number(e.target.value);if(Number.isInteger(n)&&n>=0&&n<=300&&n!==fresh)setFresh(n);}}/> 组／项 / 天</label></div></>;
}
