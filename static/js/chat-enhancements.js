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

  // Slash-command palette: typing / at the start of a chat message shows the
  // available learning commands, with keyboard filtering and selection.
  const slashCommands=[
    {name:'/word',hint:'Teach a word: source = Melimi'},
    {name:'/meaning',hint:'Teach a meaning: source = Melimi'},
    {name:'/content',hint:'Store and learn a block of language content'},
    {name:'/example',hint:'Store an example sentence'},
    {name:'/root',hint:'Teach a root: root = meaning'},
    {name:'/affix',hint:'Teach an affix: form = meaning'},
    {name:'/rule',hint:'Teach a language rule: name = rule'},
    {name:'/phrase',hint:'Store a phrase or expression'},
    {name:'/note',hint:'Store a language note'},
    {name:'/correct',hint:'Correct a previously taught mapping'}
  ];
  let slashBox=null, slashItems=[], slashIndex=0;

  function ensureSlashBox(){
    const input=$('#input'); if(!input)return null;
    if(slashBox)return slashBox;
    slashBox=document.createElement('div'); slashBox.className='slash-command-box hidden'; slashBox.setAttribute('role','listbox');
    input.parentElement?.appendChild(slashBox);
    return slashBox;
  }

  function hideSlashCommands(){
    if(!slashBox)return;
    slashBox.classList.add('hidden'); slashBox.innerHTML=''; slashItems=[]; slashIndex=0;
  }

  function selectSlashCommand(index){
    const input=$('#input'); if(!input||!slashItems[index])return;
    const command=slashItems[index].dataset.command;
    const value=input.value;
    const leading=value.match(/^\s*/)?.[0]||'';
    input.value=`${leading}${command} `;
    input.focus();
    input.setSelectionRange(input.value.length,input.value.length);
    hideSlashCommands();
    input.dispatchEvent(new Event('input',{bubbles:true}));
  }

  function updateSlashCommands(){
    const input=$('#input'); if(!input)return;
    const value=input.value;
    // Only activate when / is the first non-whitespace character. Once a
    // command has been selected, continue filtering until real content starts.
    const match=value.match(/^\s*\/([^\s\n]*)/);
    if(!match){hideSlashCommands();return;}
    const filter=match[1].toLowerCase();
    const visible=slashCommands.filter(command=>command.name.slice(1).toLowerCase().startsWith(filter));
    if(!visible.length){hideSlashCommands();return;}
    const box=ensureSlashBox(); if(!box)return;
    box.innerHTML=''; slashItems=[]; slashIndex=Math.min(slashIndex,visible.length-1);
    visible.forEach((command,index)=>{
      const item=document.createElement('button'); item.type='button'; item.className='slash-command-item'+(index===slashIndex?' active':''); item.dataset.command=command.name; item.setAttribute('role','option');
      item.innerHTML=`<span class="slash-command-name">${escapeHtml(command.name)}</span><span class="slash-command-hint">${escapeHtml(command.hint)}</span>`;
      item.addEventListener('mousedown',event=>{event.preventDefault();selectSlashCommand(index)});
      box.appendChild(item); slashItems.push(item);
    });
    box.classList.remove('hidden');
  }

  const input=$('#input');
  if(input){
    input.addEventListener('input',()=>{slashIndex=0;updateSlashCommands()});
    input.addEventListener('keydown',event=>{
      if(!slashBox||slashBox.classList.contains('hidden'))return;
      if(event.key==='ArrowDown'){event.preventDefault();slashIndex=(slashIndex+1)%slashItems.length;updateSlashCommands();return}
      if(event.key==='ArrowUp'){event.preventDefault();slashIndex=(slashIndex-1+slashItems.length)%slashItems.length;updateSlashCommands();return}
      if(event.key==='Tab'){event.preventDefault();selectSlashCommand(slashIndex);return}
      if(event.key==='Enter'&&!event.shiftKey){
        const value=input.value;
        if(/^\s*\/[^\s\n]*$/.test(value)&&slashItems.length){event.preventDefault();selectSlashCommand(slashIndex);return}
      }
      if(event.key==='Escape')hideSlashCommands();
    });
    document.addEventListener('click',event=>{if(slashBox&&!slashBox.contains(event.target)&&event.target!==input)hideSlashCommands()});
  }

  const slashStyle=document.createElement('style');
  slashStyle.textContent=`
    .composer{position:relative}
    .slash-command-box{position:absolute;left:0;bottom:calc(100% + 8px);width:min(420px,calc(100vw - 32px));max-height:320px;overflow:auto;padding:6px;border:1px solid rgba(255,255,255,.12);border-radius:14px;background:rgba(18,20,28,.98);box-shadow:0 16px 40px rgba(0,0,0,.35);z-index:50}
    .slash-command-box.hidden{display:none}
    .slash-command-item{display:flex;width:100%;align-items:center;gap:12px;border:0;border-radius:10px;background:transparent;color:inherit;padding:10px 12px;text-align:left;cursor:pointer}
    .slash-command-item:hover,.slash-command-item.active{background:rgba(255,255,255,.08)}
    .slash-command-name{min-width:92px;font-weight:700;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
    .slash-command-hint{opacity:.68;font-size:.86rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  `;
  document.head.appendChild(slashStyle);

  document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();$('#input')?.focus()}});
  window.addEventListener('teluai:toast',event=>{if(typeof window.toast==='function'&&event.detail)window.toast(event.detail)});
  const chat=$('#chat'); if(chat){chat.setAttribute('aria-live','polite');new MutationObserver(enhanceExistingMessages).observe(chat,{childList:true})}
  if(matchMedia('(prefers-reduced-motion: reduce)').matches)document.documentElement.dataset.reducedMotion='true';
  enhanceExistingMessages();
})();
