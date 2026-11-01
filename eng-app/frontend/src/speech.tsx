import {apiUrl} from './apiBase';
import {useSharedSetting} from './sharedSetting';
import {useEffect,useState,useRef} from 'react';

export function useLocalSpeech(){
 const iosMedia=/iPad|iPhone|iPod/.test(navigator.userAgent)||navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1;
 const supported=typeof window!=='undefined'&&'speechSynthesis' in window;
 const [voices,setVoices]=useState<SpeechSynthesisVoice[]>([]);
 const [message,setMessage]=useState('');
 const [auto,setAuto]=useSharedSetting('speech-auto',true);
 const [rate,setRate]=useSharedSetting('speech-rate',0.85);
 const [selected,setSelected]=useSharedSetting('speech-voice','');
 const [speaking,setSpeaking]=useState(false);
 const [source,setSource]=useSharedSetting('speech-source','oxford');
 const audio=useRef<HTMLAudioElement|null>(null),sequence=useRef(0),utteranceRef=useRef<SpeechSynthesisUtterance|null>(null);
 useEffect(()=>()=>{sequence.current++;audio.current?.pause();},[]);
 const preferredFemale=voices.find(v=>/\b(Zira|Jenny|Aria|Ava|Emma|Michelle|Ana|Susan|Samantha)\b/i.test(v.name));
 const voice=voices.find(v=>v.voiceURI===selected)||preferredFemale||voices[0];
 useEffect(()=>{
  if(!supported)return;
  const load=()=>setVoices(window.speechSynthesis.getVoices().filter(v=>/^en[-_]US$/i.test(v.lang)));
  load();window.speechSynthesis.addEventListener('voiceschanged',load);
  return()=>{window.speechSynthesis.removeEventListener('voiceschanged',load);window.speechSynthesis.cancel();};
 },[]);
 function stop(){sequence.current++;if(audio.current){audio.current.pause();audio.current.onerror=null;audio.current.removeAttribute('src');audio.current.load();audio.current=null;}if(supported)window.speechSynthesis.cancel();setSpeaking(false);}
 function speak(text:string){
  stop();setMessage('');
  try{const session=(navigator as any).audioSession;if(session)session.type='playback';}catch{/* Optional iOS API; normal playback still works without it. */}
  const oxford=source==='oxford'&&/^[a-z]+(?:[-'][a-z]+)*$/i.test(text.trim());
  if(oxford||iosMedia){
   const token=sequence.current,player=new Audio(apiUrl(oxford?'/api/pronunciation/oxford-us?word='+encodeURIComponent(text.trim()):'/api/pronunciation/device-us?text_value='+encodeURIComponent(text.trim())));audio.current=player;player.playbackRate=rate;
   player.onplaying=()=>{if(sequence.current===token){setSpeaking(true);setMessage('');}};player.onended=()=>{if(sequence.current===token){setSpeaking(false);setMessage('');}};
   player.onerror=()=>{if(sequence.current===token){setSpeaking(false);setMessage(oxford?'牛津录音暂不可用，请检查网络后重试。':'离线录音暂不可用，请检查电脑学习服务和语音引擎。');}};
   void player.play().catch(e=>{if(sequence.current===token&&e.name!=='AbortError'){setSpeaking(false);setMessage(e.name==='NotAllowedError'?'请点击播放按钮播放牛津发音。':'录音加载失败，请检查学习服务后重试。');}});
   return;
  }
  if(!supported){setMessage('未找到本机美式声音。请在设备设置中添加英语（美国）语音，然后重启浏览器。');return;}
  const utterance=new SpeechSynthesisUtterance(text);
  utteranceRef.current=utterance;
  const live=window.speechSynthesis.getVoices().filter(v=>/^en[-_]US$/i.test(v.lang));
  const chosen=live.find(v=>v.voiceURI===selected)||live.find(v=>v.voiceURI===voice?.voiceURI)||live[0];
  if(chosen)utterance.voice=chosen;utterance.lang='en-US';utterance.rate=rate;
  const token=sequence.current;
  const pending=setTimeout(()=>{if(sequence.current===token){setSpeaking(false);setMessage('设备朗读未启动，请检查手机媒体音量、静音和英语声音设置。');}},4000);
  utterance.onstart=()=>{clearTimeout(pending);if(sequence.current===token){setSpeaking(true);setMessage('');}};
  utterance.onend=()=>{clearTimeout(pending);if(sequence.current!==token)return;setSpeaking(false);setMessage('');utteranceRef.current=null;};
  utterance.onerror=e=>{clearTimeout(pending);if(sequence.current!==token)return;setSpeaking(false);if(e.error!=='interrupted'&&e.error!=='canceled')setMessage('设备朗读失败（'+e.error+'），请检查英语声音设置后重试。');};
  window.speechSynthesis.resume();
  window.speechSynthesis.speak(utterance);
 }
 const controls=<div className="speech-settings"><select aria-label="朗读音源" value={source} onChange={e=>{stop();setMessage('');setSource(e.target.value);}}><option value="oxford">牛津美式（单词原声）</option><option value="windows">{iosMedia?'离线美式录音':'设备美式合成语音'}</option></select>{!iosMedia&&<><span>本机美式朗读</span><select aria-label="美式声音" value={voice?.voiceURI||''} onChange={e=>{stop();setSelected(e.target.value);localStorage.setItem('speech-voice',e.target.value);}}><option value="" disabled>{voices.length?'选择声音':'未发现本机美式声音'}</option>{voices.map(v=><option key={v.voiceURI} value={v.voiceURI}>{v.name}</option>)}</select></>}<select aria-label="朗读语速" value={rate} onChange={e=>{setRate(Number(e.target.value));localStorage.setItem('speech-rate',e.target.value);}}>{[0.7,0.85,1].map(r=><option key={r} value={r}>{r}× 语速</option>)}</select><button type="button" aria-pressed={auto} onClick={()=>{setAuto(!auto);localStorage.setItem('speech-auto',auto?'off':'on');}}>自动朗读：{auto?'开':'关'}</button>{speaking&&<button type="button" onClick={stop}>停止</button>}{(message||!iosMedia&&source==='windows'&&(!supported||!voices.length))&&<small role="status">{!iosMedia&&!supported?'此浏览器不支持本机朗读。':message||'未发现本机美式声音，请安装 设备的英语（美国）语音包并重启浏览器。'}</small>}</div>;
 return {speak,stop,auto,ready:source==='oxford'||iosMedia||supported,controls,message};
}
