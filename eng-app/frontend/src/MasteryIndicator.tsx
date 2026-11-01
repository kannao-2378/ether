export function MasteryIndicator({assessment,level=0}:{assessment:any;level?:number}){
 const labels=['未学','初识','熟悉','稳固','可迁移'];
 const recentRecall=assessment?.independent_successes>0&&assessment?.latest_feedback==='clear';
 const transferable=assessment?.stable&&assessment?.transfer_contexts>=3&&assessment?.transfer_days>=2&&assessment?.transfer==='多情境、跨日使用有证据';
 const current=transferable?4:assessment?.stable?3:recentRecall?2:level>0||assessment?.last_at?1:0;
 return <div className="mastery-track" role="img" aria-label={'学习程度：'+labels[current]} title={'当前：'+labels[current]+'。未学 → 初识 → 熟悉 → 稳固 → 可迁移'}>{labels.map((label,index)=><span key={label} className={'mastery-stage '+(index<=current?'reached ':'')+(index===current?'current':'')}><i/><small>{label}</small></span>)}</div>;
}
