import {DailyOverview} from './DailyOverview';
import {MemoryCurve} from './MemoryCurve';
import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
const kinds:Record<string,string>={word:'单词',collocation:'搭配',phrase:'短语',sentence:'句子',rule:'规则'};
const ratings:Record<string,string>={clear:'认识',hard:'模糊',forgot:'忘记'};
const percent=(n:number|null)=>n===null?'暂无':Math.round(n*100)+'%';
export function LearningProfile(){
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[status,setStatus]=useState('');
 async function load(){setError('');try{const r=await learningFetch('/api/profile');if(!r.ok)throw Error('档案读取失败，请重试。');setData(await r.json());}catch(e){setError((e as Error).message);}}
 useEffect(()=>{void load();},[]);
 async function manage(action:string){if(busy)return;setBusy(true);setStatus('');try{const r=await learningFetch('/api/'+action,action==='backup'?{method:'POST'}:{});if(!r.ok)throw Error('操作失败，请重试。');const value=await r.json();if(action==='backup')setStatus('备份已保存：'+value.filename);else{const u=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='english-learning.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);setStatus('学习数据已导出。');}}catch(e){setStatus((e as Error).message);}finally{setBusy(false);}}
 const s=data?.summary,max=data?Math.max(1,...data.trend.map((d:any)=>d.attempts)):1;
 return <section className="panel learning-profile"><div className="profile-title"><button onClick={()=>void load()}>刷新</button></div>{error&&<p role="alert">{error}</p>}{!data&&!error&&<p role="status">正在读取学习记录…</p>}{data&&<>
 <DailyOverview/><h3>累计学习</h3><div className="profile-metrics">{[['累计学习天数',s.active_days,'完成过训练的自然日'],['连续学习',s.streak+' 天','允许今天尚未开始'],['已接触内容',s.touched+' 项','不等于已经掌握'],['累计完成训练',s.completed+' 次','同一题重复提交只计一次'],['独立通过率',percent(s.independent_rate),'无提示、无拼写失败且反馈认识'],['独立通过',s.independent+' 次','与最终写对分开统计']].map(([label,value,note])=><div key={label} title={String(note)}><small>{label}</small><strong>{value}</strong></div>)}</div>
 {!s.completed&&<p className="profile-empty">暂无训练记录。</p>}
 <MemoryCurve data={data.memory_curve}/>
 <h3>掌握程度分布</h3><div className="profile-mastery">{data.mastery.map((m:any,i:number)=><div key={m.label}><i className={'mastery-color mastery-'+i}/><span>{m.label}</span><strong>{m.count}</strong></div>)}</div>
 <h3>最近 30 天</h3><div className="profile-chart" role="img" aria-label="最近30天完成训练与独立通过次数"><div className="profile-bars">{data.trend.map((d:any)=><div key={d.date} title={`${d.date}：完成 ${d.attempts} 次，独立通过 ${d.independent} 次，涉及 ${d.items} 项`}><div className="profile-bar-total" style={{height:(d.attempts/max*100)+'%'}}><div className="profile-bar-independent" style={{height:(d.attempts?d.independent/d.attempts*100:0)+'%'}}/></div></div>)}</div><div className="profile-chart-axis"><span>{data.trend[0].date}</span><span>{data.trend[29].date}</span></div></div><p className="profile-chart-legend">浅色：完成 · 绿色：独立通过</p>
 <h3>各类内容</h3><div className="profile-types">{data.types.map((t:any)=><article className="profile-type" key={t.kind}><div className="profile-type-title"><strong>{kinds[t.kind]||t.kind}</strong><span>已学 {t.touched} / {t.total}</span></div><progress aria-label={(kinds[t.kind]||t.kind)+"学习进度"} value={t.touched} max={Math.max(1,t.total)}/><div className="profile-type-counts"><span>熟悉 <b>{t.familiar}</b></span><span>稳固 <b>{t.stable}</b></span><span>可迁移 <b>{t.transferable}</b></span></div></article>)}</div>
 <h3>需要巩固</h3><div className="profile-feedback"><span>认识 <b>{data.feedback.clear}</b></span><span>模糊 <b>{data.feedback.hard}</b></span><span>忘记 <b>{data.feedback.forgot}</b></span></div><p>看过答案 {s.hinted} 次 · 拼写改正 {s.spelling_failed} 次</p>{data.weak.length?<><small>待巩固 {data.weak_total} 项 · 显示前 10 项</small>{data.weak.map((w:any)=><div className="profile-weak" key={w.id}><div><strong>{w.answer}</strong><small>{w.prompt}</small></div><span>{ratings[w.feedback]} · 近期独立通过率 {percent(w.rate)}</span></div>)}</>:<p>暂无薄弱项。</p>}
 <p className="profile-dates">首次训练：{s.first_at?new Date(s.first_at).toLocaleString():'暂无'}<br/>最近训练：{s.last_at?new Date(s.last_at).toLocaleString():'暂无'}<br/>最长连续：{s.longest_streak} 天</p>
 </>}<details className="profile-data-tools"><summary>数据管理</summary><div className="actions"><button disabled={busy} onClick={()=>void manage('export')}>导出学习数据</button><button disabled={busy} onClick={()=>void manage('backup')}>创建数据库备份</button></div>{status&&<p role="status">{status}</p>}</details></section>;
}
