(() => {
  const $ = (s) => document.querySelector(s);
  const hideAccountSurface = () => {
    ['#accountMenu','#profileLink','#profile','#auth'].forEach(s => $(s)?.classList.add('hidden'));
    document.querySelector('.account')?.classList.add('hidden');
  };
  const ensureSettingsLink = () => {
    const nav=document.querySelector('.nav'); if(!nav||$('#publicSettingsLink'))return;
    const b=document.createElement('button'); b.type='button'; b.id='publicSettingsLink'; b.textContent='⚙ అమరికలు'; b.setAttribute('aria-label','అమరికలు');
    b.onclick=()=>typeof openSettings==='function'&&openSettings(); nav.appendChild(b);
  };
  const anonymousSession=async()=>{
    try{await api('/auth/me');return true;}catch(_){}
    const suffix=crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2);
    try{await api('/auth/guest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:`guest_${suffix.slice(0,12)}`,password:`TeluAI-${suffix}-anonymous`})});return true;}
    catch(error){console.error('Anonymous session initialization failed',error);return false;}
  };
  const openHistory=async()=>{
    const modal=$('#history'),list=$('#historyList');if(!modal||!list)return;
    modal.classList.remove('hidden');typeof closeMobileMenu==='function'&&closeMobileMenu();list.innerHTML='<div class="empty-state">కతనాలు లోడవుతున్నాయి…</div>';
    try{const data=await api('/conversations');const items=data.conversations||[];list.innerHTML=items.length?items.map(c=>`<button type="button" class="history-item" data-id="${esc(c.id||c.conversation_id)}"><b>${esc(c.title||c.name||'Conversation')}</b><span>${esc(c.updated_at||c.created_at||'')}</span></button>`).join(''):'<div class="empty-state">కతనాలు లేవు.</div>';list.querySelectorAll('.history-item').forEach(b=>b.onclick=()=>openConversation(b.dataset.id));}
    catch(error){list.innerHTML=`<div class="empty-state">కతనాలు లోడ్ కాలేదు.<br><small>${esc(error.message)}</small></div>`;}
  };
  const bind=(selector,event,handler)=>{const n=$(selector);if(n)n.addEventListener(event,handler);};

  hideAccountSurface();ensureSettingsLink();if(typeof applyDisplay==='function')applyDisplay();
  anonymousSession().then(ok=>{hideAccountSurface();if(ok&&typeof loadHistory==='function')loadHistory(false);});

  bind('#historyLink','click',e=>{e.preventDefault();e.stopPropagation();openHistory();});
  bind('#mobileMenu','click',()=>typeof toggleMobileMenu==='function'&&toggleMobileMenu());
  bind('#mobileBackdrop','click',()=>typeof closeMobileMenu==='function'&&closeMobileMenu());
  bind('#newChat','click',()=>typeof resetChat==='function'&&resetChat());
  bind('#closeHistory','click',()=>typeof closeModal==='function'&&closeModal('#history'));
  bind('#closeSettings','click',()=>typeof closeModal==='function'&&closeModal('#settings'));
  bind('#saveSettings','click',()=>typeof saveSettings==='function'&&saveSettings());
  bind('#resetSettings','click',()=>typeof resetSettings==='function'&&resetSettings());
  bind('#send','click',()=>typeof send==='function'&&send($('#input')?.value.trim()));
  bind('#input','keydown',e=>{if(e.key==='Escape'){closeModal('#settings');closeModal('#history');closeMobileMenu();}if(e.key==='Enter'&&!e.shiftKey&&readUI().enterToSend!==false){e.preventDefault();send(e.target.value.trim());}});
  bind('#input','input',e=>{e.target.style.height='auto';e.target.style.height=Math.min(e.target.scrollHeight,150)+'px';});
  document.querySelectorAll('[data-theme]').forEach(b=>b.addEventListener('click',()=>typeof applyTheme==='function'&&applyTheme(b.dataset.theme)));
  document.querySelectorAll('.suggestion').forEach(b=>b.addEventListener('click',()=>typeof send==='function'&&send(b.dataset.message||'')));
})();
