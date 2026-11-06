// Session-memory reads only; never persist private learning records in localStorage.
type Entry={response:Response;value:any;expires:number};
const entries=new Map<string,Entry>(),pending=new Map<string,Promise<Response>>();
let revision=0;
export function clearReadCache(){revision++;entries.clear();pending.clear();}
export function peekRead(key:string){const e=entries.get(key);return e&&e.expires+120000>Date.now()?e.value:null;}
export function cachedRead(key:string,ttl:number,load:()=>Promise<Response>):Promise<Response>{
 const hit=entries.get(key);if(hit&&hit.expires>Date.now())return Promise.resolve(hit.response.clone());
 const current=pending.get(key);if(current)return current.then(r=>r.clone());
 const version=revision;
 const task=load().then(async r=>{if(r.ok&&revision===version){const value=await r.clone().json().catch(()=>null);if(revision===version){if(entries.size>=32)entries.delete(entries.keys().next().value!);entries.set(key,{response:r.clone(),value,expires:Date.now()+ttl});}}return r;});
 pending.set(key,task);void task.finally(()=>{if(pending.get(key)===task)pending.delete(key);}).catch(()=>{});return task.then(r=>r.clone());
}
window.addEventListener('login-required',clearReadCache);
