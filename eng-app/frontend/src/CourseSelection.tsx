export function CourseSelection({courses}:{courses:any[]}){
 const course=courses.find(c=>c.id==='general-mainline');
 return <div className="course-selection"><label>学习路线 <strong>{course?'通用英语 · 结构与表达应用':'主线加载中'}</strong></label></div>;
}