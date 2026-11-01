let csrf='';
let privateMode=false;
export function setSession(token:string|null,enabled:boolean){csrf=token||'';privateMode=enabled;}
export const isPrivateMode=()=>privateMode;
export const csrfHeaders=():Record<string,string>=>csrf?{'X-CSRF-Token':csrf}:{};
export function apiUrl(input:string){
 const base=import.meta.env.BASE_URL.replace(/\/$/,'');
 return input.startsWith('/api/')||input==='/api'?base+input:input;
}
