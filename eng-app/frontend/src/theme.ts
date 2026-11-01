declare global {
 interface Window {PELSTheme?:{read:()=>string;apply:(preference:string)=>void}}
}
export function initialTheme(){return window.PELSTheme?.read()||'system';}
export function applyTheme(preference:string){window.PELSTheme?.apply(preference);}
