/* Live Melimi knowledge refresh.
 * Refresh re-applies the latest MASTER mappings to Melimi translations already
 * visible in this chat. It does not regenerate answers or spend Groq tokens.
 *
 * A chat translation is keyed by its source meaning/word, not by the old Telugu
 * wording. Direct Telugu MASTER entries are also refreshed, e.g.
 *   /word హానికరం = చేటుకాను
 *   old: ... హానికరం ...
 *   new: ... చేటుకాను ...
 */
(function(){
  const STORE_KEY='teluai-melimi-refresh-v1';
  const WORD_RE=/[A-Za-z]+(?:['’-][A-Za-z]+)*/g;
  const TELUGU_WORD_RE=/[\u0C00-\u0C7F]+/g;
  const TELUGU_RE=/[\u0C00-\u0C7F]/;
  let refreshRunning=false;
  let lastSignature='';

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

  /* Apply direct Telugu-source MASTER mappings to assistant/Melimi text.
   * This deliberately never touches user messages. It also skips a target that
   * is already present, so a mapping cannot repeatedly rewrite itself. */
  async function refreshDirectTeluguMappings(text){
    let value=String(text||'');
    const words=[...new Set(value.match(TELUGU_WORD_RE)||[])];
    if(!words.length)return value;
    const results=await Promise.all(words.map(async word=>({word,mapped:await analyzeWord(word)})));
    for(const {word,mapped} of results){
      if(!mapped||mapped===word)continue;
      if(value.includes(mapped)&&!value.includes(word))continue;
      value=value.split(word).join(mapped);
    }
    return value;
  }

  async function refreshMessages(showToast=false){
    if(refreshRunning||typeof messages==='undefined'||!Array.isArray(messages)||!messages.length)return 0;
    const conversationKey=(typeof conversationId!=='undefined'&&conversationId)?String(conversationId):'';
    if(!conversationKey)return 0;
    refreshRunning=true;
    try{
      const overrides=readOverrides();
      let changed=0;
      for(let i=0;i<messages.length;i++){
        const msg=messages[i];
        if(!msg||msg.role!=='assistant'||!msg.content||msg.streaming)continue;

        const original=String(msg.content);
        const bilingual=sourceFromAssistant(original);
        let source=bilingual?.source||'';
        let old=bilingual?.old||'';
        let next=original;

        /* First use the source phrase when the assistant explicitly preserves it. */
        if(!source)source=nearestUserSource(i);
        if(source){
          const translated=await translatePhrase(source);
          if(translated){
            if(old)next=next.split(old).join(translated);
            else next=replaceLeadingMelimiPhrase(next,translated);
          }
        }

        /* Then apply current MASTER mappings whose source is Telugu. */
        next=await refreshDirectTeluguMappings(next);
        if(next===original)continue;

        msg.content=next;
        overrides[conversationKey] ||= {};
        if(msg.id!=null)overrides[conversationKey][String(msg.id)]=next;
        changed++;
      }
      if(changed){
        writeOverrides(overrides);
        if(typeof renderAll==='function')renderAll();
      }
      if(showToast&&typeof toast==='function')toast(changed?`Melimi chat refreshed · ${changed} message${changed===1?'':'s'} updated`:'Melimi knowledge refreshed · no chat words changed');
      return changed;
    }finally{refreshRunning=false}
  }

  async function autoRefresh(){
    try{
      if(typeof messages==='undefined'||!Array.isArray(messages))return;
      /* A new /word command is a strong signal that MASTER changed; don't wait
         for the periodic timer when the command has just appeared. */
      const signature=messages.filter(x=>x?.role==='user'&&/^\s*\/word\b/i.test(String(x.content||''))).map(x=>String(x.content||'')).join('\n');
      if(signature!==lastSignature){lastSignature=signature;await refreshMessages(false);return;}
      await refreshMessages(false);
    }catch(e){console.debug('Melimi auto-refresh:',e)}
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
        setTimeout(autoRefresh,0);
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
        await refreshMessages(true);
        if(typeof loadHistory==='function')await loadHistory();
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

    /* Keep automatic refresh responsive. MASTER updates are deterministic and
       local; this polling does not call Groq. */
    setTimeout(autoRefresh,500);
    setInterval(autoRefresh,3000);
    window.addEventListener('focus',autoRefresh);
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
  else install();
})();
