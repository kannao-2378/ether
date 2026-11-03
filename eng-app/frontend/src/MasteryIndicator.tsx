export function MasteryIndicator({assessment,level=0}:{assessment:any;level?:number}){
 const labels=['未学','初识','熟悉','稳固'];
 const recentRecall=assessment?.independent_successes>0&&assessment?.latest_feedback==='clear';
 const current=assessment?.stable?3:recentRecall?2:level>0||assessment?.last_at?1:0;
 const transfer=assessment?.transfer_label||'未验证';
 return <div className="mastery-evidence"><div className="mastery-track" role="img" aria-label={'记忆：'+labels[current]} title={'记忆状态：'+labels[current]}>{labels.map((label,index)=><span key={label} className={'mastery-stage '+(index<=current?'reached ':'')+(index===current?'current':'')}><i/><small>{label}</small></span>)}</div><span className={'transfer-state '+(assessment?.transferable?'transfer-proven':'')} title="迁移能力独立判断，不要求先达到记忆稳固">迁移：{transfer}</span></div>;
}
