import { initReveal, initScaledSection } from '../shared-modules.js?v=11';

export function init(root){
  initScaledSection(root,746);
  initReveal(root);
  root.querySelectorAll('[data-copy]').forEach((button)=>{
    const label=button.querySelector('[data-copy-label]');
    const originalText=label?label.textContent:'';
    button.addEventListener('click',async()=>{
      try{
        await navigator.clipboard.writeText(button.dataset.copy);
        if(label) label.textContent='已复制';
        window.setTimeout(()=>{if(label) label.textContent=originalText;},1600);
      }catch{
        if(label) label.textContent=button.dataset.copy;
      }
    });
  });
}
