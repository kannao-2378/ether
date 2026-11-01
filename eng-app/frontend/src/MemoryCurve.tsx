import {useState} from 'react';
export function MemoryCurve({data}:{data:any}){
 const [day,setDay]=useState(7);
 if(!data)return null;
 const x=(d:number)=>46+d/30*530,y=(r:number)=>222-r*190;
 const path=(key:string)=>data.points.map((p:any,i:number)=>`${i?'L':'M'}${x(p.day)},${y(p[key])}`).join(' ');
 const selected=data.points.find((p:any)=>p.day===day);
 return <section className="memory-curve"><h3 title="不复习时的独立回忆概率预测">记忆曲线</h3>
 <div className="curve-status"><span>系统算法：{data.algorithm}</span><span>目标保留率：{Math.round(data.target_retention*100)}%</span><span>{data.items?`个人预测：已纳入 ${data.items} 项`:'个人预测：暂用默认值'}</span></div>
 <svg viewBox="0 0 610 265" role="img" aria-label="30天记忆预测曲线，虚线为默认预测，实线为个人预测，圆点为实际跨天复习结果">
 {[0,.25,.5,.75,1].map(r=><g key={r}><line x1="46" x2="576" y1={y(r)} y2={y(r)} className="curve-grid"/><text x="37" y={y(r)+4} textAnchor="end">{r*100}%</text></g>)}
 {[0,1,3,7,14,21,30].map(d=><text key={d} x={x(d)} y="245" textAnchor="middle">{d}天</text>)}
 <path d={path('default')} className="curve-default"/><path d={path('personal')} className="curve-personal"/>
 <line x1={x(day)} x2={x(day)} y1="32" y2="222" className="curve-grid"/>
 {data.observations.filter((p:any)=>p.day<=30).map((p:any,i:number)=><circle key={i} cx={x(p.day)} cy={y(p.rate)} r="5" className="curve-observed"><title>间隔约 {p.day.toFixed(1)} 天：{p.count} 次真实验证，独立通过 {Math.round(p.rate*100)}%</title></circle>)}
 </svg>
 <div className="curve-legend"><span className="curve-default-key">┄ 系统默认预测</span><span className="curve-personal-key">━ 个人预测</span><span className="curve-observed-key">● 实际验证</span></div>
 <label className="curve-slider">查看第 {day} 天<input aria-label="查看间隔天数" type="range" min="0" max="30" value={day} onChange={e=>setDay(Number(e.target.value))}/></label>
 <p>默认预计 {Math.round(selected.default*100)}% · 个人预计 {Math.round(selected.personal*100)}%</p>
 <small>默认模型参数 · 跨日验证 {data.delayed_samples} 次</small>
 </section>;
}
