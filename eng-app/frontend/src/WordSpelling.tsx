import {useLayoutEffect,useRef,useState,MutableRefObject} from 'react';
import {learningFetch} from './testMode';
import {isMobileLayout} from './useViewport';

type Props={question:any;inputRef:MutableRefObject<HTMLInputElement|null>;peek:boolean;english:string;draft:string;onDraft:(value:string,complete:boolean)=>void;onFocusChange:(value:boolean)=>void};
const clean=(value:string)=>value.replace(/\s/g,'').replace(/’/g,"'").replace(/[.!?。！？]+$/,'');

export function WordSpelling({question:q,inputRef,peek,english,draft,onDraft,onFocusChange}:Props){
 const initial:number[][]=q.answer_shapes||[q.word_lengths||[q.answer_length||1]];
 const [shapes,setShapes]=useState(initial),[words,setWords]=useState<string[]>(draft?draft.split(/\s+/):[]);
 const [active,setActive]=useState(0),[valid,setValid]=useState<number[]>([]),[wrong,setWrong]=useState(-1),[error,setError]=useState(false);
 const fields=useRef<(HTMLInputElement|null)[]>([]),values=useRef(words),options=useRef(initial),verified=useRef<number[]>([]);
 const generation=useRef(0),busy=useRef(false),buffer=useRef(''),alive=useRef(true),ime=useRef(false),move=useRef(false);
 const onDraftRef=useRef(onDraft);onDraftRef.current=onDraft;
 useLayoutEffect(()=>{alive.current=true;if(values.current[0])void verify(0);return()=>{alive.current=false;generation.current++;};},[]);
 useLayoutEffect(()=>{inputRef.current=fields.current[active];if(move.current){move.current=false;inputRef.current?.focus({preventScroll:true});const end=inputRef.current?.value.length||0;inputRef.current?.setSelectionRange(end,end);}},[active,inputRef]);
 const lengths=shapes[0]||initial[0];
 const limit=(i:number)=>Math.max(...options.current.map(s=>s[i]||0),1);
 const publish=(next:string[],complete=false)=>{values.current=next;setWords(next);onDraftRef.current(next.join(' ').trimEnd(),complete);};
 const focusAt=(i:number)=>{move.current=true;setActive(i);if(active===i){fields.current[i]?.focus({preventScroll:true});move.current=false;}};

 async function verify(i:number){
  const word=values.current[i]||'';
  if(!word||!options.current.some(s=>s[i]===word.length))return;
  const token=++generation.current;busy.current=true;setError(false);
  try{
   const r=await learningFetch('/api/check-word',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:globalThis.crypto?.randomUUID?.()||Date.now()+'-'+Math.random(),question_id:q.question_id,word_index:i,answer:values.current.slice(0,i+1).join(' ')})});
   if(!r.ok)throw Error();const result=await r.json();
   if(!alive.current||token!==generation.current)return;
   busy.current=false;
   if(!result.correct){setWrong(result.pending?-1:i);if(result.pending&&buffer.current){const pending=buffer.current;buffer.current='';feed(i,pending);}else buffer.current='';return;}
   options.current=result.answer_shapes;setShapes(result.answer_shapes);setWrong(-1);
   verified.current=[...verified.current.filter(n=>n<i),i];setValid(verified.current);
   if(result.complete){buffer.current='';publish(values.current,true);return;}
   const next=i+1;focusAt(next);
   if(buffer.current){const pending=buffer.current;buffer.current='';feed(next,pending);}
   else if(values.current[next])void verify(next);
  }catch{
   if(alive.current&&token===generation.current){busy.current=false;buffer.current='';setError(true);}
  }
 }
 function edit(i:number,value:string){
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
 return <div className="word-spelling" onClick={e=>e.stopPropagation()}>
  <div className="word-slots">{lengths.map((n,i)=><input key={i} ref={node=>{fields.current[i]=node;if(i===active)inputRef.current=node;}} aria-label={'第'+(i+1)+'个单词'} aria-invalid={!peek&&wrong===i} className={!peek&&wrong===i?'word-wrong':''} value={peek?(english.trim().split(/\s+/)[i]||''):(words[i]||'')} style={{width:n+'ch'}} maxLength={limit(i)} readOnly={peek&&!isMobileLayout()||i>firstUnverified&&firstUnverified>=0} autoCapitalize="none" autoCorrect="off" autoComplete="off" spellCheck={false} lang="en"
   onPointerDown={e=>{if(!peek&&firstUnverified>=0&&i>firstUnverified){e.preventDefault();focusAt(firstUnverified);}}}
   onFocus={()=>{setActive(i);onFocusChange(true);}} onBlur={()=>onFocusChange(false)}
   onChange={e=>{if(!peek)edit(i,e.target.value);}}
   onCompositionStart={()=>{ime.current=true;}} onCompositionEnd={e=>{ime.current=false;edit(i,e.currentTarget.value);}}
   onKeyDown={e=>{if(e.key===' '){e.preventDefault();return;}if(peek)return;if(e.key==='Backspace'&&!words[i]&&i>0){e.preventDefault();edit(i-1,(words[i-1]||'').slice(0,-1));focusAt(i-1);return;}if(busy.current&&!e.ctrlKey&&!e.metaKey&&e.key.length===1){e.preventDefault();buffer.current+=clean(e.key);}}}
   onBeforeInput={(e:any)=>{const data=e.data??e.nativeEvent?.data;if(!peek&&busy.current&&data&&!ime.current){e.preventDefault();buffer.current+=clean(data);}}}
   onPaste={e=>{if(peek)return;e.preventDefault();const text=clean(e.clipboardData.getData('text'));edit(i,'');feed(i,text);}}
  />)}</div>
  {error&&<button className="word-check-retry" onClick={()=>void verify(active)}>检查失败，点击重试</button>}
 </div>;
}
