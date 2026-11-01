const names:Record<string,string>={n:'名词',v:'动词',vt:'及物动词',vi:'不及物动词',adj:'形容词',a:'形容词',adv:'副词',ad:'副词',pron:'代词',prep:'介词',conj:'连词',num:'数词',interj:'感叹词',int:'感叹词',det:'限定词',aux:'助动词'};
export function MeaningLines({meaning,pos,type}:{meaning:string;pos?:string;type?:string}){
 const fallback=pos||(type==='collocation'?'搭配':type==='phrase'?'短语':'');
 return <div className="meaning-lines">{(meaning||'').replace(/\\n/g,'\n').split('\n').filter(s=>s.trim()).map((line,index)=>{
  const match=line.trim().match(/^(n|vt|vi|v|adj|adv|a|ad|pron|prep|conj|num|interj|int|det|aux)\.\s*(.+)$/i);
  const label=match?`${match[1]}. ${names[match[1].toLowerCase()]}`:fallback;
  return <div className="meaning-line" key={index}>{label&&<span className="meaning-pos">{label}</span>}<span>{match?match[2]:line}</span></div>;
 })}</div>;
}
