import {useEffect,useState} from 'react';
import {useSharedSetting} from './sharedSetting';
export function DailyLimits(){
 const [message,setMessage]=useState('');
 useEffect(()=>{const show=(e:Event)=>setMessage((e as CustomEvent).detail);window.addEventListener('settings-status',show);return()=>window.removeEventListener('settings-status',show);},[]);
 const [review,setReview]=useSharedSetting('daily-review-limit',30);
 const [fresh,setFresh]=useSharedSetting('daily-new-limit',10);
 return <>{message&&<p role="status">{message}</p>}<div className="daily-limits" title="每日上限，修改后自动保存；重复练习不重复计数"><span className="daily-limits-title">每日</span><label>复习 <input key={'r'+review} type="number" defaultValue={review} min={0} max={300} onBlur={e=>{const n=Number(e.target.value);if(Number.isInteger(n)&&n>=0&&n<=300&&n!==review)setReview(n);}}/> 组 / 天</label><label>新学 <input key={'n'+fresh} type="number" defaultValue={fresh} min={0} max={300} onBlur={e=>{const n=Number(e.target.value);if(Number.isInteger(n)&&n>=0&&n<=300&&n!==fresh)setFresh(n);}}/> 组 / 天</label></div></>;
}
