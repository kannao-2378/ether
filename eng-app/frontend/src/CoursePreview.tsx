export function CoursePreview({course}:{course:any}){
 const groups=course.groups||[];
 const units=(Array.from(new Set(groups.map((g:any)=>g.unit))) as string[]).sort();
 return <section aria-label="课程试学进度"><h3>{course.title}</h3>
 <small>{groups.filter((g:any)=>g.passed).length}/{groups.length} 组基础通过 · 情境题 {course.transfer_questions} 条</small>
 {course.pack==='mainline'?<details><summary>8阶段 · 148课题 · 729目标</summary>
 {units.map(unit=><details key={unit}><summary>{unit} · {groups.filter((g:any)=>g.unit===unit).length}课题</summary>
 {groups.filter((g:any)=>g.unit===unit).map((g:any)=><div className="row" key={g.id}><span>{g.topic_id} {g.objective}</span><small>{g.passed?'基础通过':g.blockers?'待先修':'可练习'}</small></div>)}
 </details>)}<small>计数为核心书写课程。听说、讨论等能力需另取证，不由拼写自动认证。</small></details>:
 groups.map((g:any)=><div className="row" key={g.id}><span>{g.title}</span><small>{g.passed?'已通过当前基础':g.blockers?'待基础材料':'待练习'}</small></div>)}
 </section>;
}
