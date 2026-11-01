import {useEffect,useState} from 'react';
import {apiUrl,csrfHeaders,setSession} from './apiBase';
export function AuthGate({children}:{children:(logout?:()=>void)=>React.ReactNode}){
 const [state,setState]=useState<any>(null),[password,setPassword]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function load(){
  setError('');
  try{const r=await fetch(apiUrl('/api/auth/status'),{credentials:'same-origin',cache:'no-store'});if(!r.ok)throw Error('连接失败，请重试');const data=await r.json();setSession(data.csrf,data.enabled);if(data.enabled)sessionStorage.removeItem('learning-test');setState(data);}
  catch(e){setError((e as Error).message);}
 }
 useEffect(()=>{void load();const expired=()=>{setSession(null,true);setState({enabled:true,authenticated:false});setError('登录已过期，请重新登录。');};window.addEventListener('login-required',expired);return()=>window.removeEventListener('login-required',expired);},[]);
 async function login(e:React.FormEvent){e.preventDefault();if(busy)return;setBusy(true);setError('');try{
  const r=await fetch(apiUrl('/api/auth/login'),{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});const data=await r.json();if(!r.ok)throw Error(data.detail||'登录失败');setPassword('');setSession(data.csrf,data.enabled);setState(data);
 }catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function logout(){if(busy)return;setBusy(true);setError('');try{const r=await fetch(apiUrl('/api/auth/logout'),{method:'POST',credentials:'same-origin',headers:csrfHeaders()});if(!r.ok&&r.status!==401)throw Error('退出失败，请重试');setSession(null,true);setState({enabled:true,authenticated:false});}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 if(state?.authenticated)return <>{children(state.enabled?()=>void logout():undefined)}</>;
 return <main className="login-screen"><section className="login-card"><div className="brand">循序<span>ENGLISH LEARNING</span></div><h1>个人英语学习</h1>{!state?<><p>正在连接学习服务…</p>{error&&<p role="alert">{error}</p>}<button onClick={()=>void load()}>重新连接</button></>:<form onSubmit={login}><label htmlFor="learning-password">学习密码</label><input id="learning-password" type="password" autoComplete="current-password" required maxLength={1024} value={password} onChange={e=>setPassword(e.target.value)}/>{error&&<p role="alert">{error}</p>}<button type="submit" disabled={busy}>{busy?'正在登录…':'登录学习'}</button></form>}</section></main>;
}
