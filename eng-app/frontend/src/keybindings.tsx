import {useSharedSetting} from './sharedSetting';
export const defaultKeys={clear:'1',hard:'2',forgot:'3',familiar:'4',peek:'Control',audio:'Enter',submit:'Enter',contextAudio:'Alt+Enter'};
export function eventKey(e:KeyboardEvent){return (e.altKey&&e.key!=='Alt'?'Alt+':'')+e.key;}
export function useKeybindings(){return useSharedSetting('keybindings',defaultKeys);}
export function KeybindingSettings(){
 const [keys,setKeys]=useKeybindings();
 const options=['1','2','3','4','5','6','7','8','9','F2','F3','F4','F6','F7','F8','F9','Enter','Control','Alt+Enter'];
 const names:Record<string,string>={clear:'认识（释义页）',hard:'模糊（释义页）',forgot:'忘记（释义页）',familiar:'我已熟悉，测试升级',peek:'按住查看答案，松开隐藏',audio:'发音（所有练习）'};
 return <section className="keybinding-settings"><h2>快捷键设置</h2><p>Enter 固定用于发音；句子填完整后自动检查。</p>{Object.entries(names).map(([id,label])=><label key={id}>{label}<select aria-label={label} value={keys[id as keyof typeof keys]} onChange={e=>{const next={...keys,[id]:e.target.value};const entries=Object.entries(next).filter(([id])=>id in names);const conflict=entries.some(([a,v],i)=>entries.slice(i+1).some(([b,w])=>v===w&&!([a,b].includes('audio')&&[a,b].includes('submit'))));if(conflict){alert('这个按键已绑定其他功能，请先调整另一项。');return;}setKeys(next);}}>{options.filter(key=>key!=='Enter'||id==='audio').map(key=><option value={key} key={key}>{key==='Control'?'Ctrl':key}</option>)}</select></label>)}<button onClick={()=>setKeys(defaultKeys)}>恢复默认快捷键</button></section>;
}
