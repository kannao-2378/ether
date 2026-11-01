import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
export function FocusTraining({id}:{id:string}){
 const [data,setData]=useState<any>(null),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(''),[added,setAdded]=useState(false);
 useEffect(()=>{let active=true;setData(null);setAdded(false);setMessage('');setError('');learningFetch('/api/focus/'+encodeURIComponent(id)).then(async r=>{if(!r.ok)throw Error('专项内容读取失败');return r.json();}).then(d=>{if(active){setData(d);setAdded(d.requests.some((r:any)=>['pending','active'].includes(r.status)));}}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[id]);
 async function add(){if(busy)return;setBusy(true);setError('');try{const r=await learningFetch('/api/focus/'+encodeURIComponent(id),{method:'POST'});if(!r.ok)throw Error('加入失败，请重试');await r.json();setAdded(true);setMessage('已加入今日专项');window.dispatchEvent(new Event('focus-updated'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 const labels:Record<string,string>={word:'单词',collocation:'搭配',phrase:'短语',sentence:'句子'};
 return <section className="focus-training"><h4>专项训练</h4>{error&&<p role="alert">{error}</p>}{data&&<><small>{Object.entries(data.counts).map(([k,n])=>`${labels[k]||k} ${n}`).join(' · ')}</small><p>使用词库中已登记的相关内容，先学习再书写验证。{data.items.length===1&&'目前只有这个词条，尚无配套搭配或句子。'}</p><div className="actions"><button disabled={busy||added} onClick={()=>void add()}>{added?'已加入今日专项':'加入今日专项'}</button>{added&&<button onClick={()=>window.dispatchEvent(new Event('enter-next-stage'))}>开始特训</button>}</div><small>手动追加，不占自动新学／复习额度；活动训练仍最多 12 组。</small>{message&&<p role="status">{message}</p>}</>}</section>;
}
