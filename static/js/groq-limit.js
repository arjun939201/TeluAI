(()=>{
  const KEY='teluai-groq-limit-until';
  let timer=null;
  const state={lastLock:0};
  function elements(){return {area:document.querySelector('.composer-area'),form:document.querySelector('#composer'),input:document.querySelector('#input')||document.querySelector('#messageInput'),send:document.querySelector('#send')||document.querySelector('#sendButton')}}
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
    const m=Math.floor(s/60),sec=s%60;
    return m>0?`${m}m ${String(sec).padStart(2,'0')}s`:`${sec}s`;
  }
  function lock(until){
    until=Math.max(Date.now()+1000,Number(until)||0);
    localStorage.setItem(KEY,String(until));
    state.lastLock=until;
    const {input,send}=elements(),box=ensureTimer();
    if(!box)return;
    clearInterval(timer);
    const tick=()=>{
      const left=Number(localStorage.getItem(KEY)||0)-Date.now();
      if(left<=0){unlock();return}
      if(input){input.disabled=true;input.setAttribute('placeholder','Groq limit reached — please wait…')}
      if(send){send.disabled=true;send.setAttribute('aria-disabled','true');send.title='Groq rate limit reached'}
      box.style.display='block';
      box.textContent=`Grok limit reached · try again in ${format(left)}`;
    };
    tick();
    timer=setInterval(tick,1000);
  }
  function unlock(){
    clearInterval(timer);timer=null;localStorage.removeItem(KEY);
    const {input,send}=elements(),box=ensureTimer();
    if(input){input.disabled=false;input.removeAttribute('aria-disabled');input.setAttribute('placeholder','మేలిమి తెలుగులో అడుగు...')}
    if(send){send.disabled=false;send.removeAttribute('aria-disabled');send.title=''}
    if(box){box.style.display='none';box.textContent=''}
  }
  function parseSeconds(text){
    const value=String(text||'').toLowerCase();
    let total=0,found=false;
    const h=value.match(/(\d+(?:\.\d+)?)\s*h/),m=value.match(/(\d+(?:\.\d+)?)\s*m/),s=value.match(/(\d+(?:\.\d+)?)\s*s/);
    if(h){total+=Number(h[1])*3600;found=true}
    if(m){total+=Number(m[1])*60;found=true}
    if(s){total+=Number(s[1]);found=true}
    if(found)return Math.max(1,Math.ceil(total));
    const n=value.match(/(?:retry-after|try again in|retry in|reset(?:s| in)?)[^0-9]*(\d+(?:\.\d+)?)/);
    return n?Math.max(1,Math.ceil(Number(n[1]))):60;
  }
  function isLimit(status,text){
    return status===429||/(rate.?limit|too many requests|quota|try again in|retry-after|tokens per day|tokens per minute|requests per minute|requests per day|limit reached)/i.test(String(text||''));
  }
  async function inspectResponse(response){
    if(!response||response.status<400)return;
    try{
      const retryAfter=response.headers?.get('retry-after');
      const reset=response.headers?.get('x-ratelimit-reset')||response.headers?.get('x-ratelimit-reset-requests');
      const copy=response.clone();
      const raw=await copy.text().catch(()=>'' );
      let data=null;
      try{data=JSON.parse(raw)}catch{}
      const detail=data?.detail||data?.message||data?.error?.message||data?.error||raw||'';
      if(!isLimit(response.status,detail))return;
      let seconds=retryAfter?parseSeconds(retryAfter):0;
      if(!seconds&&reset){
        const n=Number(String(reset).trim());
        if(Number.isFinite(n)){
          // Groq may expose a duration such as 2m30s or an epoch timestamp.
          seconds=n>Date.now()/1000?Math.ceil(n-Date.now()/1000):parseSeconds(reset);
        }
      }
      if(!seconds)seconds=parseSeconds(detail);
      lock(Date.now()+seconds*1000);
    }catch(e){console.debug('Groq limit detection failed',e)}
  }
  const originalFetch=window.fetch.bind(window);
  window.fetch=async(...args)=>{
    const response=await originalFetch(...args);
    inspectResponse(response);
    return response;
  };
  function restore(){
    const until=Number(localStorage.getItem(KEY)||0);
    if(until>Date.now())lock(until);else unlock();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',restore);else restore();
})();
