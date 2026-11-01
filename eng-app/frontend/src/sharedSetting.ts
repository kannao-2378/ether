import {learningFetch} from './testMode';
import {useEffect,useState} from 'react';
export function useSharedSetting<T>(key:string,initial:T):[T,(value:T)=>void]{
 const [value,setValue]=useState(initial);
 useEffect(()=>{
  let active=true;
  const load=()=>learningFetch('/api/settings').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{if(active&&data[key]!==undefined)setValue(data[key]);}).catch(()=>{});
  void load();window.addEventListener('focus',load);
  const timer=setInterval(load,5000);
  return()=>{active=false;clearInterval(timer);window.removeEventListener('focus',load);};
 },[key]);
 function save(next:T){
  learningFetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({[key]:next})}).then(async r=>{if(!r.ok)throw Error(`HTTP ${r.status}`);const saved=await r.json();setValue(saved[key]);window.dispatchEvent(new CustomEvent('settings-status',{detail:'设置已保存'}));}).catch(e=>window.dispatchEvent(new CustomEvent('settings-status',{detail:`设置未保存：${e.message}。请重试。`})));
 }
 return [value,save];
}
