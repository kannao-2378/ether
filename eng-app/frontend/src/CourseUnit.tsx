import {useState} from 'react';
import {learningFetch} from './testMode';
export function CourseUnit({unit}:{unit:any}){
 const [data,setData]=useState<any>(null),[page,setPage]=useState(1),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 async function load(n=1){setLoading(true);setError('');try{const r=await learningFetch('/api/curriculum/units/'+encodeURIComponent(unit.id)+'?page='+n);if(!r.ok)throw Error();setData(await r.json());setPage(n);}catch{setError('单元内容读取失败，请重试。');}finally{setLoading(false);}}
 return <details id={'course-unit-'+unit.id} className="curriculum-unit" onToggle={e=>{if(e.currentTarget.open&&!data&&!loading)void load();}}><summary><span>{unit.title}</span><small>{unit.total} 项 · 已接触 {unit.introduced} · 回忆通过 {unit.recalled}</small></summary><p>{unit.goal}</p>{loading&&<p role="status">正在读取本单元…</p>}{error&&<button onClick={()=>void load(page)}>{error}</button>}<div className="course-item-list">{data?.items.map((i:any)=><div key={i.id}><span>{i.answer}<small>{i.prompt}</small></span><small>{i.level>=3?'回忆通过':i.introduced?'练习中':'未学'}</small></div>)}</div>{data?.total_pages>1&&<div className="actions"><button disabled={loading||page===1} onClick={()=>void load(page-1)}>上一页</button><span>{page}/{data.total_pages}</span><button disabled={loading||page===data.total_pages} onClick={()=>void load(page+1)}>下一页</button></div>}</details>;
}
