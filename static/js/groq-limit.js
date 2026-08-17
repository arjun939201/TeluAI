(()=>{
  const KEY='teluai-groq-limit-until';
  let timer=null;
  function elements(){return {area:document.querySelector('.composer-area'),form:document.querySelector('#composer'),input:document.querySelector('#input')||document.querySelector('#messageInput'),send:document.querySelector('#send')||document.querySelector('#sendButton')}}
  function ensureTimer(){
    const {area}=elements();
    if(!area)return null;
    let box=document.getElementById('groqLimitTimer');
    if(!box){
      box=document.createElement('div');box.id='groqLimitTimer';box.setAttribute('role','status');box.setAttribute('aria-live','polite');box.style.display='none';box.style.textAlign='center';box.style.fontSize='13px';box.style.margin='0 0 8px';box.style.opacity='.9';area.insertBefore(box,area.firstChild)
    }
    return box;
  }
  function format(ms){const s=Math.max(0,Math.ceil(ms/1000)),m=Math.floor(s/60),sec=s%60;return m>0?`${m}m ${String(sec).padStart(2,'0')}s`:`${sec}s`}
  function lock(until){
    until=Math.max(Date.now()+1000,Number(until)||0);localStorage.setItem(KEY,String(until));
    const {input,send}=elements(),box=ensureTimer();if(!box)return;
    clearInterval(timer);
    const tick=()=>{const left=Number(localStorage.getItem(KEY)||0)-Date.now();if(left<=0){unlock();return}if(input){input.disabled=true;input.setAttribute('placeholder','Groq limit reached — please wait…')}if(send){send.disabled=true;send.setAttribute('aria-disabled','true');send.title='Groq rate limit reached'}box.style.display='block';box.textContent=`Groq limit reached · try again in ${format(left)}`};
    tick();timer=setInterval(tick,1000)
  }
  function unlock(){clearInterval(timer);timer=null;localStorage.removeItem(KEY);const {input,send}=elements(),box=ensureTimer();if(input){input.disabled=false;input.removeAttribute('aria-disabled');input.setAttribute('placeholder','మేలిమి తెలుగులో అడుగు...')}if(send){send.disabled=false;send.removeAttribute('aria-disabled');send.title=''}if(box){box.style.display='none';box.textContent=''}}
  function parseSeconds(value){const text=String(value||'').trim().toLowerCase();const h=text.match(/(\d+(?:\.\d+)?)\s*h/),m=text.match(/(\d+(?:\.\d+)?)\s*m/),s=text.match(/(\d+(?:\.\d+)?)\s*s/);let total=0;if(h)total+=Number(h[1])*3600;if(m)total+=Number(m[1])*60;if(s)total+=Number(s[1]);if(total)return Math.max(1,Math.ceil(total));const n=Number(text);return Number.isFinite(n)&&n>0?Math.max(1,Math.ceil(n)):60}
  async function inspectResponse(response){
    if(!response||response.status!==429)return;
    try{const retry=response.headers?.get('retry-after');const copy=response.clone();const raw=await copy.text().catch(()=>''),data=(()=>{try{return JSON.parse(raw)}catch{return null}})(),detail=data?.detail;const code=typeof detail==='object'?detail?.code:data?.code;if(code!=='groq_rate_limit')return;const seconds=typeof detail==='object'&&detail?.retry_after_seconds?Number(detail.retry_after_seconds):parseSeconds(retry);lock(Date.now()+seconds*1000)}catch(e){console.debug('Groq limit detection failed',e)}
  }
  const originalFetch=window.fetch.bind(window);window.fetch=async(...args)=>{const response=await originalFetch(...args);inspectResponse(response);return response};
  window.teluaiGroqLimitLock=(seconds)=>lock(Date.now()+Math.max(1,Number(seconds)||60)*1000);
  function restore(){const until=Number(localStorage.getItem(KEY)||0);if(until>Date.now())lock(until);else unlock()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',restore);else restore();
})();
