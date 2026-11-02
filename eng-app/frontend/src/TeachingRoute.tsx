export function TeachingRoute({route}:{route:any}){
 if(!route)return null;
 const names:Record<string,string>={recalled:'本组训练通过',learning:'练习中',ready:'可学习',blocked:'先补基础'};
 return <section className="teaching-route"><h2>课程路线</h2><p>{route.ready_total} 组已编排 · {route.truncated?'当前展示中训练通过':'本组训练通过'} {route.recalled}</p>{route.truncated&&<small>当前展示前 200 个目标；排课使用完整课程。</small>}{!route.ready_total&&<p>本课程暂无已编排的新课；资料仍可在词典查看或加入专项。</p>}{route.units.map((u:any)=><details key={u.id} open={u.id===route.current_unit}><summary><span>{u.title}{u.id===route.current_unit&&<small> · 当前可学</small>}</span><small>{u.recalled}/{u.total}</small></summary><p>{u.goal}</p>{u.items.map((i:any)=><div className="teaching-goal" key={i.id}><div><strong>{i.english}</strong><small>{i.chinese}</small></div><div><span>{names[i.state]}</span>{i.blockers.map((b:any)=><small key={b.id}>{b.reason}</small>)}</div></div>)}</details>)}<small>待编排资料 {route.draft_total} 组，不自动作为新课。回忆通过不等于长期稳固。</small></section>;
}
