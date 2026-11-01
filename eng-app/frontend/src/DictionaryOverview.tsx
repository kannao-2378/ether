export function DictionaryPagination({data,page,onPage,position='顶部'}:{data:any;page:number;onPage:(n:number)=>void;position?:string}){
 const size=data?.page_size||30,total=data?.total??0,pages=data?.total_pages??Math.ceil(total/size);
 return <nav className="dictionary-pagination" aria-label={position+'词典翻页'}><span>{data?`第 ${pages?page:0} / ${pages} 页 · ${total} 项`:'正在读取页数…'}</span><div><button disabled={!data||page<=1} onClick={()=>onPage(page-1)}>上一页</button><label>跳至 <select aria-label={position+'词典页码'} disabled={!pages} value={pages?page:0} onChange={e=>onPage(Number(e.target.value))}>{!pages&&<option value={0}>—</option>}{Array.from({length:pages},(_,n)=><option key={n+1} value={n+1}>{n+1}</option>)}</select> 页</label><button disabled={!data||page>=pages} onClick={()=>onPage(page+1)}>下一页</button></div></nav>;
}
export function DictionaryOverview({data,page,onPage}:{data:any;page:number;onPage:(n:number)=>void}){
 const pages=data?.total_pages??(data?Math.ceil(data.total/30):null);
 return <div className="dictionary-overview"><div className="content-totals"><div><strong>{data?.total_all??data?.total??'—'}</strong><span>总数</span></div><div><strong>{data?.total??'—'}</strong><span>筛选结果</span></div><div><strong>{pages??'—'}</strong><span>页数</span></div></div><DictionaryPagination data={data} page={page} onPage={onPage}/></div>;
}
