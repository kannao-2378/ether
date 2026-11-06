type Variant={shape:number[];hashes:string[];pending:string[][]};
export async function localWordCheck(proof:{salt:string;variants:Variant[]}|undefined,index:number,given:string){
 if(!proof||!globalThis.crypto?.subtle||/[^\x00-\x7f]/.test(given.replace(/’/g,"'")))return null;
 const normalized=given.replace(/’/g,"'").trim().replace(/\s+/g,' ').toLowerCase().replace(/[.!?。！？]+$/,'').trimEnd();
 let bytes:ArrayBuffer;try{bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(proof.salt+normalized));}catch{return null;}
 const hash=Array.from(new Uint8Array(bytes),v=>v.toString(16).padStart(2,'0')).join('');
 const matching=proof.variants.filter(v=>v.hashes[index]===hash);
 return {correct:matching.length>0,pending:matching.length===0&&proof.variants.some(v=>v.pending[index]?.includes(hash)),complete:matching.some(v=>v.shape.length===index+1),answer_shapes:matching.map(v=>v.shape)};
}
