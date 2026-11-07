// Session-memory reads only; never persist private learning records in localStorage.
// Stale-while-revalidate: a cached entry past its TTL is served immediately and
// refreshed in the background, so pages open instantly after the first visit.
type Entry={response:Response;value:any;expires:number};
const entries=new Map<string,Entry>(),pending=new Map<string,Promise<Response>>();
const STALE_WINDOW=600000;
let revision=0;
export function clearReadCache(){revision++;entries.clear();pending.clear();}
// Domain-aware invalidation: only drop keys starting with the given prefixes.
export function invalidateReadCache(prefixes:string[]){
 if(!prefixes.length)return;
 revision++;
 for(const key of [...entries.keys()])if(prefixes.some(p=>key.startsWith(p))){entries.delete(key);pending.delete(key);}
}
export function peekRead(key:string){const e=entries.get(key);return e&&e.expires+STALE_WINDOW>Date.now()?e.value:null;}
function store(key:string,ttl:number,load:()=>Promise<Response>):Promise<Response>{
 const current=pending.get(key);if(current)return current.then(r=>r.clone());
 const version=revision;
 const task=load().then(async r=>{if(r.ok&&revision===version){const value=await r.clone().json().catch(()=>null);if(revision===version){if(entries.size>=64)entries.delete(entries.keys().next().value!);entries.set(key,{response:r.clone(),value,expires:Date.now()+ttl});}}return r;});
 pending.set(key,task);void task.finally(()=>{if(pending.get(key)===task)pending.delete(key);}).catch(()=>{});
 return task.then(r=>r.clone());
}
export function cachedRead(key:string,ttl:number,load:()=>Promise<Response>):Promise<Response>{
 const hit=entries.get(key);
 if(hit&&hit.expires>Date.now())return Promise.resolve(hit.response.clone());
 if(hit&&hit.expires+STALE_WINDOW>Date.now()){void store(key,ttl,load).catch(()=>{});return Promise.resolve(hit.response.clone());}
 return store(key,ttl,load);
}
window.addEventListener('login-required',clearReadCache);
