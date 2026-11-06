import {localWordCheck} from './localWordCheck';
import {useLayoutEffect,useRef,useState,MutableRefObject} from 'react';
import {learningFetch} from './testMode';

type Props={question:any;inputRef:MutableRefObject<HTMLInputElement|null>;peek:boolean;english:string;draft:string;onDraft:(value:string,complete:boolean)=>void;onFocusChange:(value:boolean)=>void};
const clean=(value:string)=>value.replace(/\s/g,'').replace(/’/g,"'").replace(/[.!?。！？]+$/,'');

export function WordSpelling({question:q,inputRef,peek,english,draft,onDraft,onFocusChange}:Props){
 const initial:number[][]=q.answer_shapes||[q.word_lengths||[q.answer_length||1]];
 const [shapes,setShapes]=useState(initial),[words,setWords]=useState<string[]>(draft?draft.split(/\s+/):[]);
 const [active,setActive]=useState(0),[valid,setValid]=useState<number[]>([]),[wrong,setWrong]=useState(-1),[error,setError]=useState(false);
 const editor=useRef<HTMLInputElement|null>(null),slots=useRef<(HTMLSpanElement|null)[]>([]),container=useRef<HTMLDivElement|null>(null);
 const values=useRef(words),options=useRef(initial),verified=useRef<number[]>([]);
 const reports=useRef<{body:any;done:boolean;work:Promise<void>}[]>([]);
 const editRevision=useRef(0),requestAttempt=useRef({key:'',id:''});
 const generation=useRef(0),busy=useRef(false),buffer=useRef(''),alive=useRef(true),ime=useRef(false);
 const onDraftRef=useRef(onDraft);onDraftRef.current=onDraft;
 useLayoutEffect(()=>{alive.current=true;if(values.current[0])void verify(0);return()=>{alive.current=false;generation.current++;};},[]);
 // Keep one actual editing node mounted: an asynchronous word check must not
 // blur one native iOS input and attempt to open another outside a user gesture.
 const position=()=>{const field=editor.current,slot=slots.current[active],box=container.current;if(!field||!slot||!box)return;const r=slot.getBoundingClientRect(),b=box.getBoundingClientRect();Object.assign(field.style,{left:(r.left-b.left)+'px',top:(r.top-b.top)+'px',width:r.width+'px',height:getComputedStyle(slot).lineHeight});};
 useLayoutEffect(()=>{inputRef.current=editor.current;position();});
 useLayoutEffect(()=>{const observer=new ResizeObserver(position);if(container.current)observer.observe(container.current);window.visualViewport?.addEventListener('resize',position);return()=>{observer.disconnect();window.visualViewport?.removeEventListener('resize',position);};},[active]);
 const lengths=shapes[0]||initial[0];
 const limit=(i:number)=>Math.max(...options.current.map(s=>s[i]||0),1);
 const publish=(next:string[],complete=false)=>{values.current=next;setWords(next);onDraftRef.current(next.join(' ').trimEnd(),complete);};
 const focusAt=(i:number,userGesture=false)=>{setActive(i);if(userGesture&&editor.current!==document.activeElement)editor.current?.focus({preventScroll:true});};

 async function verify(i:number){
  const word=values.current[i]||'';
  if(!word||!options.current.some(s=>s[i]===word.length))return;
  const token=++generation.current;busy.current=true;setError(false);
  const attemptKey=i+':'+values.current.slice(0,i+1).join(' ')+':'+editRevision.current;
  if(requestAttempt.current.key!==attemptKey)requestAttempt.current={key:attemptKey,id:globalThis.crypto?.randomUUID?.()||Math.random().toString(36).slice(2)};
  try{
   const body={id:requestAttempt.current.id,question_id:q.question_id,word_index:i,answer:values.current.slice(0,i+1).join(' ')};
   const send=()=>learningFetch('/api/check-word',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
   let result=await localWordCheck(q.word_validation,i,body.answer);
   if(!result){const r=await send();if(!r.ok)throw Error();result=await r.json();}
   else if(!result.correct&&!result.pending){
    const entry={body,done:false,work:Promise.resolve()};reports.current.push(entry);
    entry.work=send().then(r=>{if(!r.ok)throw Error();entry.done=true;}).catch(()=>{if(alive.current)setError(true);});
   }
   if(!result)throw Error();
   if(!alive.current||token!==generation.current)return;
   busy.current=false;
   if(!result.correct){setWrong(result.pending?-1:i);if(result.pending&&buffer.current){const pending=buffer.current;buffer.current='';feed(i,pending);}else buffer.current='';return;}
   options.current=result.answer_shapes;setShapes(result.answer_shapes);setWrong(-1);
   verified.current=[...verified.current.filter(n=>n<i),i];setValid(verified.current);
   if(result.complete){
    await Promise.all(reports.current.map(r=>r.work));
    for(const report of reports.current.filter(r=>!r.done)){const r=await learningFetch('/api/check-word',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(report.body)});if(!r.ok)throw Error();report.done=true;}
    if(!alive.current||token!==generation.current)return;
    buffer.current='';publish(values.current,true);return;
   }
   const next=i+1;focusAt(next);
   if(buffer.current){const pending=buffer.current;buffer.current='';feed(next,pending);}
   else if(values.current[next])void verify(next);
  }catch{
   if(alive.current&&token===generation.current){busy.current=false;buffer.current='';setError(true);}
  }
 }
 function edit(i:number,value:string){
  editRevision.current++;
  generation.current++;busy.current=false;buffer.current='';setWrong(-1);setError(false);
  const compatible=initial.filter(s=>values.current.slice(0,i).every((w,j)=>s[j]===w.length));
  options.current=compatible.length?compatible:initial;setShapes(options.current);
  verified.current=verified.current.filter(n=>n<i);setValid(verified.current);
  const next=[...values.current];next[i]=clean(value).slice(0,Math.max(...initial.map(s=>s[i]||0),1));
  publish(next);setActive(i);
  if(!ime.current)void verify(i);
 }
 function feed(i:number,text:string){
  const added=clean(text),next=[...values.current],size=(next[i]||'').length;
  const stops=options.current.map(s=>s[i]||0).filter(n=>n>size),stop=stops.length?Math.min(...stops):limit(i),room=stop-size;
  next[i]=(next[i]||'')+added.slice(0,Math.max(0,room));
  buffer.current+=added.slice(Math.max(0,room));publish(next);void verify(i);
 }
 const firstUnverified=lengths.findIndex((_,i)=>!valid.includes(i));
 return <div ref={container} className="word-spelling" onClick={e=>e.stopPropagation()}>
  <div className="word-slots" aria-hidden="true">{lengths.map((n,i)=><span key={i} ref={node=>{slots.current[i]=node;}} className={'word-slot'+(!peek&&wrong===i?' word-wrong':'')+(i===active?' editing-slot':'')} style={{width:n+'ch'}} onClick={()=>{if(!peek)focusAt(firstUnverified>=0&&i>firstUnverified?firstUnverified:i,true);}}>{peek?(english.trim().split(/\s+/)[i]||''):(words[i]||'')}</span>)}</div>
  <input ref={editor} className={'word-editor'+(!peek&&wrong===active?' word-wrong':'')} aria-label={'第'+(active+1)+'个单词'} aria-invalid={!peek&&wrong===active} value={peek?(english.trim().split(/\s+/)[active]||''):(words[active]||'')} maxLength={limit(active)} autoCapitalize="none" autoCorrect="off" autoComplete="off" spellCheck={false} lang="en"
   onFocus={()=>onFocusChange(true)} onBlur={()=>onFocusChange(false)}
   onChange={e=>{if(!peek)edit(active,e.target.value);}}
   onCompositionStart={()=>{ime.current=true;}} onCompositionEnd={e=>{ime.current=false;if(!peek)edit(active,e.currentTarget.value);}}
   onKeyDown={e=>{if(e.key===' '){e.preventDefault();return;}if(peek)return;if(e.key==='Backspace'&&!words[active]&&active>0){e.preventDefault();edit(active-1,(words[active-1]||'').slice(0,-1));focusAt(active-1);return;}if(busy.current&&!e.ctrlKey&&!e.metaKey&&e.key.length===1){e.preventDefault();buffer.current+=clean(e.key);}}}
   onBeforeInput={(e:any)=>{const data=e.data??e.nativeEvent?.data;if(!peek&&busy.current&&data&&!ime.current){e.preventDefault();buffer.current+=clean(data);}}}
   onPaste={e=>{e.preventDefault();if(peek)return;const text=clean(e.clipboardData.getData('text'));edit(active,'');feed(active,text);}}
  />
  {error&&<button className="word-check-retry" onClick={()=>void verify(active)}>检查失败，点击重试</button>}
 </div>;
}
