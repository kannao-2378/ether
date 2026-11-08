import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';

async function call(path:string,body?:unknown){
 const r=await learningFetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const d=await r.json().catch(()=>null);
 if(!r.ok)throw Error(typeof d?.detail==='string'?d.detail:`请求失败（${r.status}）`);
 return d;
}

export function UserCourseImport(){
 const [source,setSource]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[imported,setImported]=useState<any>(null);
 const [courses,setCourses]=useState<any[]>([]),[listError,setListError]=useState(''),[listBusy,setListBusy]=useState(true);
 const [expandedId,setExpandedId]=useState(''),[courseContent,setCourseContent]=useState<any>(null),[contentBusy,setContentBusy]=useState(false);

 async function refreshCourses(){
  setListBusy(true);
  try{const data=await call('/api/user-courses');setCourses(Array.isArray(data)?data:[]);setListError('');}
  catch(e){setListError(e instanceof Error?e.message:'课程列表读取失败');}
  finally{setListBusy(false);}
 }
 useEffect(()=>{void refreshCourses();},[]);

 async function loadFile(file?:File){if(!file)return;try{setSource(await file.text());setMessage(`已读取 ${file.name}`);setError('');}catch{setError('无法读取该文件。');}}
 async function importCourse(){
  setBusy(true);setError('');setMessage('');setImported(null);
  try{
   let value;try{value=JSON.parse(source);}catch(e){throw Error(`JSON格式错误：${e instanceof Error?e.message:'无法解析'}`);}
   const d=await call('/api/user-courses/import',{course:value});
   setMessage(`已导入「${d.title}」：${d.groups}组、${d.items}项。`);
   setImported({id:d.id,title:d.title,course:value});
   await refreshCourses();
  }catch(e){setError(e instanceof Error?e.message:'导入失败');}
  finally{setBusy(false);}
 }
 async function toggleCourse(course:any){
  if(expandedId===course.id){setExpandedId('');setCourseContent(null);return;}
  setExpandedId(course.id);setCourseContent(null);setContentBusy(true);setListError('');
  try{const data=await call(`/api/user-courses/${encodeURIComponent(course.id)}`);setCourseContent(data.course);}
  catch(e){setListError(e instanceof Error?e.message:'课程内容读取失败');}
  finally{setContentBusy(false);}
 }

 return <section className="user-course-panel">
  <h2>导入自定课程</h2>
  <p>选择 JSON 文件或直接粘贴。系统会校验整份30组课程；任何错误都会拒绝整份导入并报告组号和字段。</p>
  <label className="user-course-file">选择 JSON 文件<input type="file" accept=".json,application/json" onChange={e=>void loadFile(e.target.files?.[0])}/></label>
  <label>粘贴课程 JSON<textarea rows={9} value={source} onChange={e=>setSource(e.target.value)} placeholder={'{"title":"我的课程","groups":[...]}'}/></label>
  <div className="user-study-actions">
   <button disabled={busy||!source.trim()} onClick={()=>void importCourse()}>{busy?'正在校验…':'校验并导入整份课程'}</button>
   <button onClick={()=>window.dispatchEvent(new Event('enter-next-stage'))}>开始今日学习</button>
  </div>
  {message&&<p role="status">{message}</p>}
  {imported&&<details><summary>查看本次导入的 JSON</summary><pre className="user-course-error">{JSON.stringify(imported.course,null,2)}</pre></details>}
  {error&&<pre role="alert" className="user-course-error">{error}</pre>}
  <div className="user-course-list">
   <h3>已导入课程</h3>
   {listBusy&&<p>正在读取课程列表…</p>}
   {listError&&<p role="alert" className="user-course-error">{listError}</p>}
   {!listBusy&&!courses.length&&!listError&&<p>还没有导入课程。</p>}
   {courses.map(course=><article className="user-course-list-item" key={course.id}>
    <div><strong>{course.title}</strong><small>{course.groups}组 · {course.items}项 · 导入于 {new Date(course.created_at).toLocaleDateString()}</small></div>
    <button type="button" disabled={contentBusy&&expandedId===course.id} onClick={()=>void toggleCourse(course)}>{expandedId===course.id?'收起课程内容':'查看课程内容'}</button>
    {expandedId===course.id&&<div className="user-course-list-content">{contentBusy?<p>正在读取课程内容…</p>:courseContent&&<pre>{JSON.stringify(courseContent,null,2)}</pre>}</div>}
   </article>)}
  </div>
 </section>;
}
