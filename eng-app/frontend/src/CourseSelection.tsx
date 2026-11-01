import {useSharedSetting} from './sharedSetting';
export function CourseSelection({courses}:{courses:any[]}){
 const [selected,save]=useSharedSetting('active-course','all');
 return <div className="course-selection"><label>新学课程 <select aria-label="当前新学课程" value={selected} onChange={e=>save(e.target.value)}><option value="all">全部课程</option>{courses.map(c=><option key={c.id} value={c.id}>{c.title} · {c.total} 项</option>)}</select></label></div>;
}
