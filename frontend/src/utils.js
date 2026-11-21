export const safe=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fixed=(value,n=1)=>value==null?'—':Number(value).toFixed(n);
export const dataFrom=form=>Object.fromEntries(new FormData(form));
export const pause=ms=>new Promise(r=>setTimeout(r,ms));
export const localTime=x=>x?new Date(x+'Z').toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'尚未记录';
export const minutesLabel=value=>value==null?'待定':`${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`;
// Same key on a retried click: the server replays the first result instead of booking twice.
export const stableKey=(node,scope)=>{if(!node.dataset.requestKey)node.dataset.requestKey=`${scope}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,10)}`;return node.dataset.requestKey;};
export const clearKey=(node)=>{delete node.dataset.requestKey;};
export function message(text){const el=document.querySelector('#message');el.textContent=text;el.classList.add('visible');clearTimeout(window.solarMessage);window.solarMessage=setTimeout(()=>el.classList.remove('visible'),4500);}
