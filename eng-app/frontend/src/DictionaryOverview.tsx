import {useState,useEffect} from 'react';
export function DictionaryPagination({data,page,onPage,position='顶部'}:{data:any;page:number;onPage:(n:number)=>void;position?:string}){
 const [jump,setJump]=useState(String(page));useEffect(()=>setJump(String(page)),[page]);
 const size=data?.page_size||30,total=data?.total??0,pages=data?.total_pages??Math.ceil(total/size);
 return <nav className="dictionary-pagination" aria-label={position+'词典翻页'}><span>{data?`第 ${pages?page:0} / ${pages} 页 · ${total} 项`:'正在读取页数…'}</span><div><button disabled={!data||page<=1} onClick={()=>onPage(page-1)}>上一页</button><label>跳至 <input type="number" min={1} max={pages||1} aria-label={position+'词典页码'} disabled={!pages} value={jump} style={{width:'4.5em'}} onChange={e=>setJump(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&pages)onPage(Math.max(1,Math.min(pages,Number(jump)||1)))}} onBlur={()=>{if(pages)onPage(Math.max(1,Math.min(pages,Number(jump)||1)))}}/> 页</label><button disabled={!data||page>=pages} onClick={()=>onPage(page+1)}>下一页</button></div></nav>;
}
export function DictionaryOverview({data,page,onPage}:{data:any;page:number;onPage:(n:number)=>void}){
 const pages=data?.total_pages??(data?Math.ceil(data.total/30):null);
 return <div className="dictionary-overview"><div className="content-totals"><div><strong>{data?.total_all??data?.total??'—'}</strong><span>知识记录（含新旧条目）</span></div><div><strong>{data?.total??'—'}</strong><span>筛选结果</span></div><div><strong>{pages??'—'}</strong><span>页数</span></div></div><div className="dictionary-kind-totals">{[['word','单词'],['collocation','搭配'],['phrase','短语'],['sentence','句子']].map(([k,label])=><span key={k}>{label} <b>{data?.type_counts?.[k]??'—'}</b></span>)}</div><small>按知识记录分类，包含不同义项和课程条目，不等于去重词汇量；下载例句已统一计入句子。</small><DictionaryPagination data={data} page={page} onPage={onPage}/></div>;
}
