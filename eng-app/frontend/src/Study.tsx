import {KnowledgeContent} from './KnowledgeContent';
import {MeaningLines} from './MeaningLines';
import {RecentHistory} from './RecentHistory';
import {useEffect,useRef,useState} from 'react';
import {isMobileLayout,hasDesktopInput} from './useViewport';

export function Study(p:any){
 const input=useRef<HTMLInputElement>(null);
 const keyboardWasOpen=useRef(false),lastKeyboardTouch=useRef(0);
 const [inputFocused,setInputFocused]=useState(false);
 const [metadata,setMetadata]=useState<any>(null);
 const [rest,setRest]=useState(false);
 useEffect(()=>{if(p.q?.kind!=='done')setRest(false);},[p.q?.kind]);

 const q=p.q;
 const revealed=q?.kind==='learn'||p.checked?.correct||p.hint||p.result;
 const item=p.current;
 useEffect(()=>{if(hasDesktopInput()&&q?.kind==='recall'&&!revealed&&!p.busy)input.current?.focus({preventScroll:true});setInputFocused(Boolean(input.current&&document.activeElement===input.current));},[q?.question_id,q?.kind,!!revealed,p.busy]);
 const pronunciation=metadata&&metadata.id===q?.id?metadata.details:null;
 const english=q?.answer||p.checked?.answer||p.hint?.answer||p.result?.expected||item?.answer||'';

 const focus=()=>input.current?.focus({preventScroll:true});
 const keyboardOpen=()=>{
  if(!input.current||document.activeElement!==input.current)return false;
  const ios=/iPad|iPhone|iPod/.test(navigator.userAgent)||navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1;
  return !ios||!window.visualViewport||window.innerHeight-window.visualViewport.height>160;
 };
 const toggleKeyboard=(wasOpen=keyboardOpen())=>{
  const field=input.current;if(!field)return;
  if(wasOpen)field.blur();
  else{if(document.activeElement===field)field.blur();focus();} // Same scroll-free focus as tapping the input area.
 };
 const hasDraft=Boolean(p.answer);
 const lengths:number[]=q?.word_lengths||((item?.answer||'').trim().replace(/[.!?。！？]+$/,'').split(/\s+/).map((w:string)=>w.length));
 const sentence=lengths.length>1;

 return <div className={'memo-study'+(hasDraft?' has-draft':'')+(q?.kind==='recall'&&!revealed?' is-writing':'')}><div className="memo-toolbar"><button onClick={p.back} disabled={p.previousDisabled} aria-label="上一项">‹</button>{p.reviewing&&<span className="review-mode-label">回看模式</span>}<span className="study-task-counts" title={'按组／项计数；新学表达组 '+(p.newBreakdown?.expression??0)+'、独立单词 '+(p.newBreakdown?.word??0)}>复习 {p.reviewCount??0}  · 新学 {p.newCount??0}</span></div>
 {!q||q.kind==='done'?<div className="memo-empty"><h2>{!q?'正在恢复学习…':rest?'今日学习结束':'今日内容已完成'}</h2><p>{!q?'正在读取课程与进度。':rest?'进度已保存，明天继续。':q.context_round_complete?q.message:'还想继续学新内容吗？'}</p>{q?.kind==='done'&&(q.context_round_complete?<button disabled={p.busy} onClick={p.next}>开始下一轮情境题</button>:!rest?<><div className="memo-extra-options">{[10,20,50].map(amount=><button key={amount} disabled={p.busy} onClick={()=>p.extendDaily(amount)}>再学 {amount} 组</button>)}</div>{p.busy&&<small role="status">正在安排新内容…</small>}<button className="memo-rest" disabled={p.busy} onClick={()=>setRest(true)}>今天不学了</button></>:<button className="memo-rest" onClick={()=>setRest(false)}>还是想再学一些</button>)}</div>:<>
 <div className="memo-heading" role="button" tabIndex={0} aria-label="播放当前内容发音" onPointerDown={e=>e.preventDefault()} onClick={p.pronounce} onKeyDown={e=>{if(e.key===' '){e.preventDefault();p.pronounce();}}}><div className="heading-stack"><h2 className={revealed?'':'recall-title'}>{revealed?english:q.prompt}</h2><div className="heading-pronunciation" aria-hidden={!revealed||!pronunciation}>{revealed&&pronunciation&&<>{pronunciation.ipa_us&&<span className="phonetic-link">{pronunciation.ipa_us}</span>}{pronunciation.syllables&&<span>{pronunciation.syllables} · {pronunciation.stress}</span>}{!pronunciation.ipa_us&&pronunciation.pronunciation_parts?.map((part:any)=><span key={part.en}>核心词 {part.en} <span className="phonetic-link">{part.ipa}</span> · {part.syllables}（{part.stress}）</span>)}</>}</div></div></div>
 <div className="memo-meaning"><div className="memo-meaning-text">{revealed?<MeaningLines meaning={q.prompt} pos={pronunciation?.pos} type={pronunciation?.entry_type}/>:item?.stage===4?'请独立写出完整英文句子':'请写出对应的英文'}</div></div>{!revealed&&<div className="memo-section-title memo-example-title concealed" aria-hidden="true"/>}
 {q.kind==='recall'&&!revealed&&<div className={'memo-writing '+(sentence?'sentence-writing ':'')+(p.checked?.correct===false?'wrong':'')} onClick={focus}><input ref={input} onFocus={()=>setInputFocused(true)} onBlur={()=>setInputFocused(false)} autoCapitalize="none" autoCorrect="off" aria-label="英文搭配答案" value={p.peek?(item?.answer||''):p.answer} maxLength={sentence?500:(q.answer_length??item?.answer.length)} style={sentence?{width:(lengths.reduce((a,b)=>a+b,0)+lengths.length-1)+'ch',maxWidth:'100%',textAlign:'left',padding:'4px 0'}:undefined} placeholder={sentence?'':'点击或直接开始输入'} spellCheck={false} autoComplete="off" readOnly={p.peek&&!isMobileLayout()} onCompositionStart={p.compositionStart} onCompositionEnd={p.compositionEnd} onChange={e=>{if(p.peek&&isMobileLayout())p.peekEnd?.();p.change(e);}}/>{sentence&&<div className="sentence-guide" aria-label="按单词长度分段" aria-hidden={p.peek}>{lengths.map((n,i)=><span key={i} style={{width:n+'ch'}}/>)}</div>}<div className="writing-status" role="status">{p.checking?'正在检查…':p.checked?.correct===false?<span className="spelling-error">拼写不正确，请修改</span>:''}</div></div>}
 {revealed&&<div className="memo-content"><KnowledgeContent id={q.id} speak={p.speak} study onLoaded={setMetadata}/><RecentHistory id={q.id} groupId={q.group_id} revision={p.selectedFeedback}/></div>}
 {p.checked?.correct===false&&p.checked?.analysis?.map((line:string)=><p className="transfer-feedback" key={line}>{line}</p>)}
 {p.checked?.correct&&p.checked?.notices?.map((line:string)=><p className="transfer-feedback" key={line}>{line}</p>)}
 {p.speechMessage&&<p className="transfer-feedback desktop-speech-status" role="status">{p.speechMessage}</p>}
 {p.checkError&&<button className="memo-retry" onClick={p.retry}>{p.checkError}</button>}

 <div className="memo-bottom">{p.canSkip&&<button className="test-skip-button" disabled={p.busy||p.checking} onClick={p.skip}>跳过，标为会了（仅测试）</button>}{revealed?<div className="memo-ratings">{[['clear','认识','1'],['hard','模糊','2'],['forgot','忘记','3']].map(([v,l,k])=><button key={v} aria-pressed={p.selectedFeedback===v} className={v+(p.selectedFeedback===v?' feedback-selected':'')} disabled={p.busy||p.checking} onClick={()=>p.submit(v)}>{l}<kbd>{p.keys?.[v]||k}</kbd>{p.selectedFeedback===v&&<span className="feedback-check" aria-label="上次选择">√</span>}</button>)}</div> :<><div className="mobile-playback-status" role="status">{p.speechMessage}</div><div className="mobile-study-actions"><button aria-pressed={p.peek} type="button" disabled={p.busy||p.checking} onContextMenu={e=>e.preventDefault()} onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);p.peekStart?.();}} onPointerUp={()=>p.peekEnd?.()} onPointerCancel={()=>p.peekEnd?.()} onLostPointerCapture={()=>p.peekEnd?.()}>看答案</button><button type="button" aria-label="切换键盘" aria-pressed={inputFocused} onPointerDown={e=>{keyboardWasOpen.current=keyboardOpen();e.preventDefault();}} onTouchEnd={e=>{e.preventDefault();lastKeyboardTouch.current=Date.now();toggleKeyboard(keyboardWasOpen.current);}} onPointerUp={e=>{if(e.pointerType!=='touch'){e.preventDefault();toggleKeyboard(keyboardWasOpen.current);}}} onClick={e=>{if(e.detail===0&&Date.now()-lastKeyboardTouch.current>500)toggleKeyboard();}}>键盘</button><button type="button" aria-label="播放声音" disabled={p.busy} onPointerDown={e=>e.preventDefault()} onPointerUp={e=>{e.preventDefault();p.pronounce();}} onClick={e=>{if(e.detail===0)p.pronounce();}}>播放</button></div><div className="memo-spelling-actions desktop-study-actions"><button disabled={p.busy||p.checking} onClick={focus}>验证拼写</button><button aria-label="播放声音" disabled={p.busy} onClick={p.pronounce}>▶ <kbd>{p.keys?.audio||'Enter'}</kbd></button></div></>}</div>
 </>}
 <nav className="memo-nav">{[['今日学习','◷','复习'],['搭配课程','▣','课程'],['学习档案','♙','我的']].map(([key,icon,label])=><button key={key} className={key==='今日学习'?'selected':''} onClick={()=>p.navigate(key)}><span>{icon}</span>{label}</button>)}</nav>
 </div>;
}
