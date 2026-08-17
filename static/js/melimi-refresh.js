/* Live Melimi knowledge refresh.
 * Re-applies authoritative MASTER mappings to assistant messages already visible
 * in this chat. It never regenerates answers or spends Groq tokens.
 */
(function(){
  const STORE_KEY='teluai-melimi-refresh-v1';
  const WORD_RE=/[A-Za-z]+(?:['’-][A-Za-z]+)*/g;
  const TELUGU_WORD_RE=/[\u0C00-\u0C7F]+/g;
  const TELUGU_RE=/[\u0C00-\u0C7F]/;
  let refreshRunning=false;
  let lastSignature='';
  let lastMessageSignature='';
  let autoTimer=null;

  function readOverrides(){try{return JSON.parse(localStorage.getItem(STORE_KEY)||'{}')}catch{return {}}}
  function writeOverrides(value){try{localStorage.setItem(STORE_KEY,JSON.stringify(value))}catch{}}

  function messageSignature(){
    if(typeof messages==='undefined'||!Array.isArray(messages))return '';
    return messages.map((m,i)=>`${i}:${m?.role||''}:${String(m?.id??'')}:${String(m?.content||'')}`).join('\u0001');
  }

  function parseMasterMappings(){
    const mappings={};
    if(typeof messages==='undefined'||!Array.isArray(messages))return mappings;
    for(const msg of messages){
      if(msg?.role!=='user')continue;
      const text=String(msg.content||'').trim();
      const match=text.match(/^\/word\s+([\s\S]+)$/i);
      if(!match)continue;
      for(const part of match[1].split(/\s*;\s*/)){
        const m=part.match(/^(.+?)\s*(?:=|→|->)\s*(.+?)\s*$/);
        if(!m)continue;
        const source=m[1].trim();
        const target=m[2].trim();
        if(source&&target)mappings[source]=target;
      }
    }
    return mappings;
  }

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
      const r=await fetch('/melimi/analyze?word='+encodeURIComponent(value),{credentials:'same-origin',cache:'no-store'});
      if(!r.ok)return '';
      const d=await r.json();
      return String(d.melimi_equivalent||'').trim();
    }catch{return ''}
  }

  function localMapping(word,mappings){
    return String(mappings[word]||'').trim();
  }

  async function translatePhrase(source,mappings){
    const value=String(source||'');
    const words=value.match(WORD_RE)||[];
    if(!words.length)return '';
    const mapped=await Promise.all(words.map(async word=>localMapping(word,mappings)||await analyzeWord(word)));
    if(mapped.some(x=>!x))return '';
    let index=0;
    return value.replace(WORD_RE,()=>mapped[index++]);
  }

  async function mapTeluguWord(word,mappings){
    return localMapping(word,mappings)||await analyzeWord(word);
  }

  function replaceWholeTeluguWord(text,word,replacement){
    if(!word||!replacement||word===replacement)return text;
    const escaped=word.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    return String(text).replace(new RegExp(`(?<![\\u0C00-\\u0C7F])${escaped}(?![\\u0C00-\\u0C7F])`,'g'),replacement);
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
    if(quoted&&TELUGU_RE.test(quoted[2]))return value.split(quoted[2]).join(translated);
    if(/^[\s\u0C00-\u0C7F]+$/.test(value.trim()))return translated;
    return value;
  }

  async function refreshDirectTeluguMappings(text,mappings){
    let value=String(text||'');
    const words=[...new Set(value.match(TELUGU_WORD_RE)||[])];
    if(!words.length)return value;
    const results=await Promise.all(words.map(async word=>({word,mapped:await mapTeluguWord(word,mappings)})));
    for(const {word,mapped} of results){
      if(!mapped||mapped===word)continue;
      value=replaceWholeTeluguWord(value,word,mapped);
    }
    return value;
  }

  async function refreshMessages(showToast=false){
    if(refreshRunning||typeof messages==='undefined'||!Array.isArray(messages)||!messages.length)return 0;
    const conversationKey=(typeof conversationId!=='undefined'&&conversationId)?String(conversationId):'';
    if(!conversationKey)return 0;
    const currentSig=messageSignature();
    if(!showToast&&currentSig===lastMessageSignature)return 0;
    refreshRunning=true;
    try{
      const overrides=readOverrides();
      const mappings=parseMasterMappings();
      let changed=0;
      for(let i=0;i<messages.length;i++){
        const msg=messages[i];
        if(!msg||msg.role!=='assistant'||!msg.content||msg.streaming)continue;
        const original=String(msg.content);
        const bilingual=sourceFromAssistant(original);
        let source=bilingual?.source||'';
        const old=bilingual?.old||'';
        let next=original;
        if(source){
          const translated=await translatePhrase(source,mappings);
          if(translated){
            if(old)next=next.split(old).join(translated);
            else next=replaceLeadingMelimiPhrase(next,translated);
          }
        }else{
          source=nearestUserSource(i);
          if(source){
            const translated=await translatePhrase(source,mappings);
            if(translated)next=replaceLeadingMelimiPhrase(next,translated);
          }
        }
        next=await refreshDirectTeluguMappings(next,mappings);
        if(next===original)continue;
        msg.content=next;
        overrides[conversationKey] ||= {};
        if(msg.id!=null)overrides[conversationKey][String(msg.id)]=next;
        changed++;
      }
      lastMessageSignature=messageSignature();
      if(changed){
        writeOverrides(overrides);
        if(typeof renderAll==='function')renderAll();
      }
      if(showToast&&typeof toast==='function')toast(changed?`Melimi chat refreshed · ${changed} message${changed===1?'':'s'} updated`:'Melimi knowledge refreshed · no chat words changed');
      return changed;
    }finally{refreshRunning=false}
  }

  function scheduleAutoRefresh(){
    clearTimeout(autoTimer);
    autoTimer=setTimeout(()=>autoRefresh(),100);
  }

  async function autoRefresh(force=false){
    try{
      if(typeof messages==='undefined'||!Array.isArray(messages))return;
      const signature=messages.filter(x=>x?.role==='user'&&/^\s*\/word\b/i.test(String(x.content||''))).map(x=>String(x.content||'')).join('\n');
      const messageChanged=messageSignature()!==lastMessageSignature;
      const knowledgeChanged=signature!==lastSignature;
      if(knowledgeChanged)lastSignature=signature;
      if(force||messageChanged||knowledgeChanged)await refreshMessages(false);
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
        lastMessageSignature='';
        setTimeout(()=>autoRefresh(true),0);
      };
    }

    const chatContainer=document.getElementById('chatContainer');
    if(chatContainer){
      const observer=new MutationObserver(()=>scheduleAutoRefresh());
      observer.observe(chatContainer,{childList:true,subtree:true,characterData:true});
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
      button.disabled=true;button.classList.add('spinning');
      try{
        if(typeof conversationId!=='undefined'&&conversationId&&typeof loadConversation==='function')await loadConversation(conversationId);
        lastMessageSignature='';
        await refreshMessages(true);
        if(typeof loadConversations==='function')await loadConversations();
      }catch(e){
        console.error(e);
        if(typeof toast==='function')toast('Could not refresh Melimi chat words');
      }finally{button.disabled=false;button.classList.remove('spinning');}
    });
    const spacer=topbar.querySelector('.topbar-spacer');
    if(spacer)spacer.before(button);else topbar.appendChild(button);

    setTimeout(()=>autoRefresh(true),500);
    setInterval(()=>autoRefresh(false),3000);
    window.addEventListener('focus',()=>autoRefresh(true));
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
  else install();
})();
