(()=>{
  const KEY='teluai-groq-limit-until';
  let timer=null;
  const state={};
  function elements(){return {area:document.querySelector('.composer-area'),form:document.querySelector('#composer'),input:document.querySelector('#input'),send:document.querySelector('#send')}}
  function ensureTimer(){
    const {area}=elements();
    if(!area)return null;
    let box=document.getElementById('groqLimitTimer');
    if(!box){
      box=document.createElement('div');
      box.id='groqLimitTimer';
      box.setAttribute('role','status');
      box.setAttribute('aria-live','polite');
      box.style.display='none';
      box.style.textAlign='center';
      box.style.fontSize='13px';
      box.style.margin='0 0 8px';
      box.style.opacity='.9';
      area.insertBefore(box,area.firstChild);
    }
    return box;
  }
  function format(ms){
    const s=Math.max(0,Math.ceil(ms/1000));
    const m=Math.floor(s/60), sec=s%60;
    return m>0?`${m}m ${String(sec).padStart(2,'0')}s`:`${sec}s`;
  }
  function lock(until){
    localStorage.setItem(KEY,String(until));
    const {input,send}=elements(),box=ensureTimer();
    if(!box)return;
    clearInterval(timer);
    const tick=()=>{
      const left=Number(localStorage.getItem(KEY)||0)-Date.now();
      if(left<=0){unlock();return}
      if(input){input.disabled=true;input.setAttribute('placeholder','Grok limit reached — please wait…')}
      if(send){send.disabled=true;send.setAttribute('aria-disabled','true');send.title='Grok rate limit reached'}
      box.style.display='block';
      box.textContent=`Grok limit reached · try again in ${format(left)}`;
    };
    tick();timer=setInterval(tick,1000);
  }
  function unlock(){
    clearInterval(timer);timer=null;localStorage.removeItem(KEY);
    const {input,send}=elements(),box=ensureTimer();
    if(input){input.disabled=false;input.setAttribute('placeholder','Message TeluAI…')}
    if(send){send.disabled=false;send.removeAttribute('aria-disabled');send.title=''}
    if(box){box.style.display='none';box.textContent=''}
  }
  function parseSeconds(text){
    const value=String(text||'').toLowerCase();
    let total=0,found=false;
    const h=value.match(/(\d+(?:\.\d+)?)\s*h/),m=value.match(/(\d+(?:\.\d+)?)\s*m/),s=value.match(/(\d+(?:\.\d+)?)\s*s/);
    if(h){total+=Number(h[1])*3600;found=true}if(m){total+=Number(m[1])*60;found=true}if(s){total+=Number(s[1]);found=true}
    if(found)return Math.max(1,Math.ceil(total));
    const n=value.match(/(?:retry-after|try again in|retry in)[^0-9]*(\d+(?:\.\d+)?)/);
    return n?Math.max(1,Math.ceil(Number(n[1]))):60;
  }
  function isLimit(status,text){return status===429||/(rate.?limit|too many requests|quota|try again in|retry-after|tokens per day|tokens per minute)/i.test(String(text||''))}
  const originalFetch=window.fetch.bind(window);
  window.fetch=async(...args)=>{
    const response=await originalFetch(...args);
    if(response.status===429||response.status===502){
      try{
        const copy=response.clone(),data=await copy.json().catch(()=>null);
        const text=data?.detail||data?.message||'';
        if(isLimit(response.status,text))lock(Date.now()+parseSeconds(text)*1000);
      }catch{}
    }
    return response;
  };
  function restore(){
    const until=Number(localStorage.getItem(KEY)||0);
    if(until>Date.now())lock(until);else unlock();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',restore);else restore();
})();
