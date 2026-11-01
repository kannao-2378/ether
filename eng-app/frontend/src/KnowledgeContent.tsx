import {useEffect,useState} from 'react';
import {learningFetch} from './testMode';
import {MeaningLines} from './MeaningLines';
const labels:Record<string,string>={word:'单词',collocation:'固定搭配',phrase:'短语',sentence:'句子',rule:'规则'};
const extensionTranslation=(e:any)=>e.zh||(/^相关(?:表达|用法)/.test(e.note||'')?'':(e.note||'').replace(/^对应中文[：:]\s*/,''));
export function KnowledgeContent({id,speak,study=false,onLoaded}:{id:string;speak:(s:string)=>void;study?:boolean;onLoaded?:(data:any)=>void}){
 const [data,setData]=useState<any>(null),[error,setError]=useState(''),[revision,retry]=useState(0);
 useEffect(()=>{const controller=new AbortController();setError('');learningFetch('/api/knowledge/'+encodeURIComponent(id),{signal:controller.signal}).then(async r=>{if(!r.ok)throw Error('内容读取失败');return r.json();}).then(data=>{if(!controller.signal.aborted){setData(data);onLoaded?.(data);}}).catch(e=>{if(e.name!=='AbortError')setError('内容读取失败，请重试。');});return()=>controller.abort();},[id,revision,onLoaded]);
 if(error)return <div className="knowledge-content"><button onClick={()=>retry(v=>v+1)}>{error}</button></div>;
 if(data?.id!==id)return <p className="knowledge-loading" role="status">正在读取知识说明…</p>;
 const d=data.details||{};
 return <article className="knowledge-content" aria-label="知识说明">
  {!study&&<div className="knowledge-meta">{!study&&<span className="content-kind">{labels[d.entry_type]||'知识点'}</span>}{!study&&d.ipa_us&&<button className="phonetic-link" aria-label={'朗读 '+data.answer} onClick={()=>speak(d.speech_text||data.answer)}>{d.ipa_us}</button>}{!study&&<button aria-label="朗读当前内容" onClick={()=>speak(d.speech_text||data.answer)}>▶ 发音</button>}</div>}
  {!study&&<MeaningLines meaning={data.prompt} pos={d.pos} type={d.entry_type}/>}
  {!study&&(d.syllables||d.stress)&&<p className="pronunciation-note">音节：{d.syllables} · {d.stress}</p>}
  {!study&&!d.ipa_us&&d.pronunciation_parts?.length>0&&<p className="pronunciation-note">核心词读音：{d.pronunciation_parts.map((p:any)=><span key={p.en}>{p.en} <button className="phonetic-link" aria-label={'朗读 '+p.en} onClick={()=>speak(p.en)}>{p.ipa}</button> · {p.syllables}（{p.stress}） </span>)}</p>}
  {d.use_when&&<p className="knowledge-inline-field"><strong>什么时候用：</strong>{d.use_when}</p>}
  <section className="structure-usage"><p className="knowledge-inline-field"><strong>{d.entry_type==='word'?'核心用法':'结构与用法'}：</strong>{d.structure&&<span className="structure-pattern">{d.structure}</span>}</p><p>{d.usage||data.explanation}</p>{d.sentence_parts?.length>0&&<div className="sentence-parts" aria-label="拆开看">{d.sentence_parts.map((p:any)=><span key={p.en}><b>{p.en}</b><small>{p.zh}</small></span>)}</div>}{d.knowledge_points?.filter((x:string)=>x!==d.usage).map((x:string,i:number)=><p key={i}>{x}</p>)}</section>
  {d.grammar_reference&&<details className="knowledge-more grammar-reference"><summary>语法名称（需要时再看）</summary><p>动词：表示动作的词，比如 drink（喝）。动词原形：这个词最基本的写法，比如 drink，不是 drinks 或 drinking。</p><p>主语：这句话说的是谁，比如 I（我）。动作对象：做这个动作涉及的东西，比如 drink water 里的 water（水）。有些动作后面不用接东西。</p>{d.grammar_reference.structure&&<p>{d.grammar_reference.structure}</p>}</details>}
  {d.examples?.length>0&&<section><h3>例句</h3>{d.examples.map((e:any,i:number)=><div className="content-example" key={i}><div><p>{e.en}</p>{e.zh&&<small>{e.zh}</small>}{e.source_url&&<small className="example-credit"><a href={e.source_url} target="_blank" rel="noreferrer">原句与作者</a>{e.translation_url&&<> · <a href={e.translation_url} target="_blank" rel="noreferrer">译文与作者</a></>} · {e.license||'参考语料'}</small>}</div>{!study&&<button aria-label="朗读例句" onClick={()=>speak(e.en)}>♪</button>}</div>)}</section>}
  {d.variations?.length>0&&<section className="usage-variations"><h3>组合示例</h3>{d.variations.map((v:any)=><p key={v.en}><b>{v.en}</b> · {v.zh}</p>)}</section>}
  {d.common_errors?.length>0&&<section className="common-errors"><p className="knowledge-inline-field"><strong>容易出错：</strong>{d.common_errors.join('；')}</p></section>}
  {(d.forms?.length>0||d.roots||d.root_note||d.extensions?.length>0)&&<details key={id} className="knowledge-more" open><summary>词形、词源与延伸</summary>{d.forms?.length>0&&<p className="knowledge-inline-field"><strong>词形变化：</strong>{d.forms.join(' · ')}</p>}<p className="knowledge-inline-field"><strong>词源／记忆说明：</strong>{d.roots||'无'}</p>{d.extensions?.length>0&&<><h3>延伸表达</h3>{d.extensions.map((e:any)=><p key={e.en}><b>{e.en}</b>{extensionTranslation(e)&&<> · {extensionTranslation(e)}</>}</p>)}</>}</details>}
 </article>;
}
