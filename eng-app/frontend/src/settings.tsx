import {KeybindingSettings} from './keybindings';
import {TestModeSettings} from './testMode';
import {useSharedSetting} from './sharedSetting';
import {useEffect,useState} from 'react';
import {initialTheme,applyTheme} from './theme';
export function useTheme(){
 const [theme,setTheme]=useSharedSetting<string>('interface-theme',initialTheme());
 useEffect(()=>{
  const media=matchMedia('(prefers-color-scheme: dark)');
  const apply=()=>applyTheme(theme);
  apply();media.addEventListener('change',apply);
  return()=>media.removeEventListener('change',apply);
 },[theme]);
 return {theme,setTheme};
}
export function Settings({theme,setTheme,speech,back,onLogout}:any){const [status,setStatus]=useState('');useEffect(()=>{const handler=(e:Event)=>setStatus((e as CustomEvent).detail);window.addEventListener('settings-status',handler);return()=>window.removeEventListener('settings-status',handler);},[]);return <section className="panel settings-panel"><button onClick={back}>← 返回学习</button><p role="status">{status}</p>{onLogout&&<button onClick={onLogout}>退出登录</button>}<h2>界面设置</h2><p>选择外观，跟随系统会随 设备的颜色模式自动切换。</p><div className="theme-options">{[['system','跟随系统'],['light','浅色'],['dark','深色']].map(([v,l])=><button key={v} aria-pressed={theme===v} onClick={()=>setTheme(v)}>{l}{theme===v?' ✓':''}</button>)}</div><KeybindingSettings/><TestModeSettings/><h2>朗读设置</h2><p>牛津音源用于单词美式原声。iPhone 的其他内容由学习服务离线生成录音并缓存，使用媒体音量播放；电脑继续使用所选设备声音。</p>{speech}<small className="keyboard-tip">学习时仍可按 Enter 发音。</small></section>;}
