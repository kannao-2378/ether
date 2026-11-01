import {useEffect} from 'react';
export const mobileLayout='(max-width:700px), (max-width:1000px) and (max-height:500px)';
export function isMobileLayout(){return window.matchMedia(mobileLayout).matches;}
export function useViewport(){
 useEffect(()=>{
  const view=window.visualViewport,root=document.documentElement;
  let frame=0,trackUntil=0;
  const update=()=>{
   // Safari shrinks the visual viewport, while its CSS layout height stays tall.
   // Pinch zoom should not reflow a screen the user is deliberately zooming into.
   if(view&&Math.abs(view.scale-1)>.05)return;
   const height=Math.min(view?.height||window.innerHeight,window.innerHeight);
   const set=(name:string,value:string)=>{if(root.style.getPropertyValue(name)!==value)root.style.setProperty(name,value);};
   set('--app-height',`${height}px`);
   set('--app-top',`${Math.max(0,view?.offsetTop||0)}px`);
   set('--keyboard-inset',`${Math.max(0,window.innerHeight-height)}px`);
   root.dataset.viewportCompact=height<=560?'true':'false';
   const inset=window.innerHeight-height;
   // Blur precedes the iOS keyboard closing animation. Keep the dock inset until
   // the viewport actually expands, rather than jumping as focus leaves input.
   root.dataset.keyboardOpen=inset>120||root.dataset.keyboardOpen==='true'&&inset>40||document.activeElement?.matches('.memo-writing input')&&height<=560?'true':'false';
   if(isMobileLayout()){
    const writing=document.querySelector<HTMLElement>('.memo-study.is-writing');
    // iOS can scroll overflow:hidden ancestors to reveal a focused input.
    if(writing){if(writing.scrollTop)writing.scrollTop=0;if(writing.parentElement!.scrollTop)writing.parentElement!.scrollTop=0;}
   }
  };
  const tick=()=>{frame=0;update();if(performance.now()<trackUntil)frame=requestAnimationFrame(tick);};
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(tick);};
  // Sample throughout the native animation, including Safari updates which do
  // not emit a resize event. This is a tracking window, not a delayed update.
  const trackKeyboard=()=>{trackUntil=performance.now()+1100;schedule();};
  update();view?.addEventListener('resize',schedule);view?.addEventListener('scroll',schedule);window.addEventListener('resize',schedule);
  document.addEventListener('focusin',trackKeyboard);document.addEventListener('focusout',trackKeyboard);
  return()=>{cancelAnimationFrame(frame);view?.removeEventListener('resize',schedule);view?.removeEventListener('scroll',schedule);window.removeEventListener('resize',schedule);document.removeEventListener('focusin',trackKeyboard);document.removeEventListener('focusout',trackKeyboard);delete root.dataset.viewportCompact;delete root.dataset.keyboardOpen;};
 },[]);
}
