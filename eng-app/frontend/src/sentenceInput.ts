export function sentenceReady(value:string,shapes:number[][]):boolean{
 const words=value.trim().replace(/[.!?。！？]+$/,'').trim().replace(/’/g,"'").split(/\s+/).map(w=>w.length);
 if(!value.trim()||!shapes.length)return false;
 if(shapes.some(s=>s.length===words.length&&s.every((n,i)=>n===words[i])))return true;
 // A longer accepted answer may still be in progress (I want to have a meal).
 if(shapes.some(s=>s.length>words.length&&words.every((n,i)=>i===words.length-1?n<=s[i]:n===s[i])))return false;
 return shapes.some(s=>words.length>=s.length&&words.reduce((a,b)=>a+b,0)>=s.reduce((a,b)=>a+b,0));
}
