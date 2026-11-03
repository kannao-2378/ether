// Use lengths only: never correct or reveal the learner's letters.
export function spaceByLengths(value:string,lengths:number[],cursor=value.length){
 if(lengths.length<2||lengths.some(n=>!Number.isInteger(n)||n<1))return {value,cursor};
 const compact=value.replace(/\s/g,''),before=value.slice(0,cursor).replace(/\s/g,'').length;
 const boundaries=new Set<number>();let total=0;
 lengths.slice(0,-1).forEach(n=>{total+=n;boundaries.add(total);});
 let formatted='',position=0;
 for(let i=0;i<compact.length;i++){
  if(boundaries.has(i))formatted+=' ';
  if(i===before)position=formatted.length;
  formatted+=compact[i];
 }
 if(before>=compact.length)position=formatted.length;
 return {value:formatted,cursor:position};
}

export function sentenceReady(value:string,shapes:number[][]):boolean{
 const words=value.trim().replace(/[.!?。！？]+$/,'').trim().replace(/’/g,"'").split(/\s+/).map(w=>w.length);
 if(!value.trim()||!shapes.length)return false;
 if(shapes.some(s=>s.length===words.length&&s.every((n,i)=>n===words[i])))return true;
 // A longer accepted answer may still be in progress (I want to have a meal).
 if(shapes.some(s=>s.length>words.length&&words.every((n,i)=>i===words.length-1?n<=s[i]:n===s[i])))return false;
 return shapes.some(s=>words.length>=s.length&&words.reduce((a,b)=>a+b,0)>=s.reduce((a,b)=>a+b,0));
}
