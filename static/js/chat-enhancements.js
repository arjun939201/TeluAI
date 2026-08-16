(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>\"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
  }

  function renderMarkdown(source) {
    const raw = String(source ?? '');
    const blocks = [];
    let value = raw.replace(/```([\w-]+)?\n?([\s\S]*?)```/g, (_, language, code) => {
      const index = blocks.length;
      blocks.push(`<pre class="rich-code"><code>${escapeHtml(code.trimEnd())}</code></pre>`);
      return `\u0000CODE${index}\u0000`;
    });
    value = escapeHtml(value)
      .replace(/`([^`\n]+)`/g, '<code class="rich-inline-code">$1</code>')
      .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|\n)[ \t]*[-•][ \t]+(.+)/g, '$1<span class="rich-bullet">• $2</span>')
      .replace(/\n/g, '<br>');
    return value.replace(/\u0000CODE(\d+)\u0000/g, (_, index) => blocks[Number(index)] || '');
  }

  async function submitFeedback(rating) {
    try {
      await fetch('/feedback', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({rating,text:''})});
      window.dispatchEvent(new CustomEvent('teluai:toast',{detail:'Thanks for the feedback.'}));
    } catch (_) {}
  }

  function addActions(row, value) {
    if (!row || row.classList.contains('user') || row.querySelector('.message-actions')) return;
    const actions=document.createElement('div'); actions.className='message-actions';
    const copy=document.createElement('button'); copy.type='button'; copy.className='message-action'; copy.setAttribute('aria-label','Copy response'); copy.title='Copy response'; copy.textContent='Copy';
    copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(String(value??''));copy.textContent='Copied'}catch(_){copy.textContent='Copy failed'}setTimeout(()=>{copy.textContent='Copy'},1400)});
    const up=document.createElement('button'); up.type='button'; up.className='message-action'; up.setAttribute('aria-label','Good response'); up.textContent='Good'; up.addEventListener('click',()=>submitFeedback(5));
    const down=document.createElement('button'); down.type='button'; down.className='message-action'; down.setAttribute('aria-label','Poor response'); down.textContent='Not helpful'; down.addEventListener('click',()=>submitFeedback(1));
    actions.append(copy,up,down); row.appendChild(actions);
  }

  function enhanceExistingMessages(){
    document.querySelectorAll('#chat .message.assistant').forEach(row=>{
      const bubble=$('.bubble',row); if(!bubble||bubble.dataset.richRendered==='1')return;
      const value=bubble.textContent||''; bubble.innerHTML=renderMarkdown(value); bubble.dataset.richRendered='1'; addActions(row,value);
    });
  }

  const originalAddMessage=window.addMessage;
  if(typeof originalAddMessage==='function'){
    window.addMessage=function enhancedAddMessage(value,role){
      originalAddMessage(value,role);
      if(role==='assistant'){
        const row=$('#chat .message:last-child'), bubble=$('.bubble',row);
        if(bubble){bubble.innerHTML=renderMarkdown(value);bubble.dataset.richRendered='1'}
        addActions(row,value);
      }
    };
  }

  const originalSend=window.send;
  if(typeof originalSend==='function'){
    window.send=async function enhancedSend(value){
      const button=$('#send'); button?.classList.add('is-loading'); button?.setAttribute('aria-busy','true');
      try{return await originalSend(value)}finally{button?.classList.remove('is-loading');button?.setAttribute('aria-busy','false')}
    };
  }

  const modeSelect=$('#preferredMode');
  if(modeSelect){
    if(![...modeSelect.options].some(option=>option.value==='standard'))modeSelect.add(new Option('సాధారణ తెలుగు','standard'));
    modeSelect.addEventListener('change',()=>{try{const saved=JSON.parse(localStorage.getItem('teluai_ui_settings')||'{}');saved.preferredMode=modeSelect.value;localStorage.setItem('teluai_ui_settings',JSON.stringify(saved))}catch(_) {}});
  }

  // Stable professional.js keeps its mature controller; this wrapper makes its
  // existing /chat request honor the actual mode selected in Settings.
  const nativeFetch=window.fetch.bind(window);
  window.fetch=(input,init={})=>{
    const url=typeof input==='string'?input:(input?.url||'');
    if(url.endsWith('/chat')&&init?.method==='POST'&&typeof init.body==='string'){
      try{
        const payload=JSON.parse(init.body), selected=$('#preferredMode')?.value;
        if(selected==='standard'||selected==='melimi')init={...init,body:JSON.stringify({...payload,mode:selected})};
      }catch(_) {}
    }
    return nativeFetch(input,init);
  };

  document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();$('#input')?.focus()}});
  window.addEventListener('teluai:toast',event=>{if(typeof window.toast==='function'&&event.detail)window.toast(event.detail)});
  const chat=$('#chat'); if(chat){chat.setAttribute('aria-live','polite');new MutationObserver(enhanceExistingMessages).observe(chat,{childList:true})}
  if(matchMedia('(prefers-reduced-motion: reduce)').matches)document.documentElement.dataset.reducedMotion='true';
  enhanceExistingMessages();
})();
