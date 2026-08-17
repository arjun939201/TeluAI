/* Live Melimi knowledge refresh.
 * Refresh re-applies the latest MASTER word mappings to Melimi translations
 * already visible in this chat. It does not regenerate answers or spend Groq tokens.
 */
(function(){
  const STORE_KEY='teluai-melimi-refresh-v1';
  const WORD_RE=/[A-Za-z]+(?:['’-][A-Za-z]+)*/g;
  const TELUGU_RE=/[\u0C00-\u0C7F]/;

  function readOverrides(){try{return JSON.parse(localStorage.getItem(STORE_KEY)||'{}')}catch{return {}}}
  function writeOverrides(value){try{localStorage.setItem(STORE_KEY,JSON.stringify(value))}catch{}}

  function sourceFromUser(text){
    const value=String(text||'').trim();
    let match=value.match(/^\s*\/word\s+(.+?)\s*(?:=|→|->)\s*[^\n]+$/i);
    if(match)return match[1].trim();
    match=value.match(/^\s*(.+?)\s*(?:=|→|->)\s*$/);
    return match?match[1].trim():'';
  }

  function sourceFromAssistant(text){
    const value=String(text||'');
    const match=value.match(/["“]([^"”]+)["”]\s*అనే\s*పలుకు\s*["“]([^"”]+)["”]\s*అనే\s*ఆంగ్ల/i);
    return match?{old:match[1].trim(),source:match[2].trim()}:null;
  }

  async function analyzeWord(word){
    const value=String(word||'').trim();
    if(!value)return '';
    try{
      const r=await fetch('/melimi/analyze?word='+encodeURIComponent(value),{credentials:'same-origin'});
      if(!r.ok)return '';
      const d=await r.json();
      return String(d.melimi_equivalent||'').trim();
    }catch{return ''}
  }

  async function translatePhrase(source){
    const words=String(source||'').match(WORD_RE)||[];
    if(!words.length)return '';
    const mapped=await Promise.all(words.map(analyzeWord));
    if(mapped.some(x=>!x))return '';
    let index=0;
    return String(source).replace(WORD_RE,()=>mapped[index++]);
  }

  function nearestUserSource(index){
    for(let j=index-1;j>=0;j--){
      if(messages[j]?.role!=='user')continue;
      const text=String(messages[j].content||'').trim();
      if(/^\/word\b/i.test(text))return '';
      return sourceFromUser(text);
    }
    return '';
  }

  function replaceLeadingMelimiPhrase(text,translated){
    const value=String(text||'');
    const quoted=value.match(/(["“])([^"”]+)(["”])\s*అనే\s*పలుకు/);
    if(quoted&&TELUGU_RE.test(quoted[2])){
      const old=quoted[2];
      return value.split(old).join(translated);
    }
    if(/^[\s\u0C00-\u0C7F]+$/.test(value.trim()))return translated;
    return value;
  }

  async function refreshMessages(){
    if(typeof messages==='undefined'||!Array.isArray(messages)||!messages.length)return 0;
    const overrides=readOverrides();
    const conversationKey=(typeof conversationId!=='undefined'&&conversationId)?String(conversationId):'';
    if(!conversationKey)return 0;
    let changed=0;

    for(let i=0;i<messages.length;i++){
      const msg=messages[i];
      if(!msg||msg.role!=='assistant'||!msg.content||msg.streaming)continue;

      const bilingual=sourceFromAssistant(msg.content);
      let source=bilingual?.source||'';
      let old=bilingual?.old||'';
      if(!source)source=nearestUserSource(i);
      if(!source)continue;

      const translated=await translatePhrase(source);
      if(!translated)continue;

      let next=String(msg.content);
      if(old)next=next.split(old).join(translated);
      else next=replaceLeadingMelimiPhrase(next,translated);
      if(next===msg.content)continue;

      msg.content=next;
      overrides[conversationKey] ||= {};
      if(msg.id!=null)overrides[conversationKey][String(msg.id)]=next;
      changed++;
    }

    if(changed)writeOverrides(overrides);
    if(changed&&typeof renderAll==='function')renderAll();
    return changed;
  }

  function install(){
    const topbar=document.querySelector('.topbar');
    if(!topbar||document.getElementById('melimiRefresh'))return;

    if(typeof loadConversation==='function'){
      const originalLoadConversation=loadConversation;
      loadConversation=async function(id){
        await originalLoadConversation(id);
        const overrides=readOverrides();
        const saved=overrides[String(id)]||{};
        if(typeof messages!=='undefined'&&Array.isArray(messages)){
          let changed=false;
          messages.forEach(msg=>{
            const replacement=saved[String(msg.id)];
            if(replacement&&replacement!==msg.content){msg.content=replacement;changed=true;}
          });
          if(changed&&typeof renderAll==='function')renderAll();
        }
      };
    }

    const button=document.createElement('button');
    button.id='melimiRefresh';
    button.type='button';
    button.className='icon-button';
    button.setAttribute('aria-label','Refresh Melimi knowledge and chat words');
    button.title='Refresh Melimi knowledge and chat words';
    button.textContent='↻';
    button.addEventListener('click',async()=>{
      if(button.disabled)return;
      button.disabled=true;
      button.classList.add('spinning');
      try{
        if(typeof conversationId!=='undefined'&&conversationId&&typeof loadConversation==='function')await loadConversation(conversationId);
        const changed=await refreshMessages();
        if(typeof loadHistory==='function')await loadHistory();
        if(typeof toast==='function')toast(changed?`Melimi chat refreshed · ${changed} message${changed===1?'':'s'} updated`:'Melimi knowledge refreshed · no chat words changed');
      }catch(e){
        console.error(e);
        if(typeof toast==='function')toast('Could not refresh Melimi chat words');
      }finally{
        button.disabled=false;
        button.classList.remove('spinning');
      }
    });
    const spacer=topbar.querySelector('.topbar-spacer');
    if(spacer)spacer.before(button);else topbar.appendChild(button);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
  else install();
})();
