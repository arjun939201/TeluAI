(() => {
  const $ = (s) => document.querySelector(s);
  const hideAccountSurface = () => {
    ['#accountMenu', '#profileLink', '#profile', '#auth'].forEach(s => $(s)?.classList.add('hidden'));
    const account = document.querySelector('.account');
    if (account) account.classList.add('hidden');
  };
  const ensureSettingsLink = () => {
    const nav = document.querySelector('.nav');
    if (!nav || $('#publicSettingsLink')) return;
    const button = document.createElement('button');
    button.type = 'button'; button.id = 'publicSettingsLink';
    button.textContent = '⚙ అమరికలు'; button.setAttribute('aria-label','అమరికలు');
    button.addEventListener('click', () => typeof openSettings === 'function' && openSettings());
    nav.appendChild(button);
  };
  const anonymousSession = async () => {
    try { await api('/auth/me'); return; } catch (_) {}
    const suffix = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2));
    try {
      await api('/auth/guest', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:`guest_${suffix.slice(0,12)}`, password:`TeluAI-${suffix}-anonymous`})});
    } catch (error) {
      console.error('Anonymous session initialization failed', error);
    }
  };
  const openHistory = async () => {
    const modal=$('#history'), list=$('#historyList'); if(!modal||!list)return;
    modal.classList.remove('hidden'); if(typeof closeMobileMenu==='function')closeMobileMenu();
    list.innerHTML='<div class="empty-state">కతనాలు లోడవుతున్నాయి…</div>';
    try {
      const data=await api('/conversations'); const items=data.conversations||[];
      list.innerHTML=items.length?items.map(c=>`<button type="button" class="history-item" data-id="${esc(c.id||c.conversation_id)}"><b>${esc(c.title||c.name||'Conversation')}</b><span>${esc(c.updated_at||c.created_at||'')}</span></button>`).join(''):'<div class="empty-state">కతనాలు లేవు.</div>';
      list.querySelectorAll('.history-item').forEach(b=>b.onclick=()=>openConversation(b.dataset.id));
    } catch(error){list.innerHTML=`<div class="empty-state">కతనాలు లోడ్ కాలేదు.<br><small>${esc(error.message)}</small></div>`;}
  };
  const bind = (selector,event,handler) => { const n=$(selector); if(n)n.addEventListener(event,handler); };

  // Public product surface: no guest/login/register/profile/account UI.
  hideAccountSurface(); ensureSettingsLink();
  anonymousSession().then(() => { hideAccountSurface(); if(typeof loadHistory==='function')loadHistory(false); });

  bind('#historyLink','click',e=>{e.preventDefault();e.stopPropagation();openHistory();});
  bind('#mobileMenu','click',()=>typeof toggleMobileMenu==='function'&&toggleMobileMenu());
  bind('#mobileBackdrop','click',()=>typeof closeMobileMenu==='function'&&closeMobileMenu());
  bind('#newChat','click',()=>typeof resetChat==='function'&&resetChat());
  bind('#closeHistory','click',()=>typeof closeModal==='function'&&closeModal('#history'));
  bind('#closeSettings','click',()=>typeof closeModal==='function'&&closeModal('#settings'));
  bind('#saveSettings','click',()=>typeof saveSettings==='function'&&saveSettings());
  bind('#resetSettings','click',()=>typeof resetSettings==='function'&&resetSettings());
  document.querySelectorAll('[data-theme]').forEach(b=>b.addEventListener('click',()=>typeof applyTheme==='function'&&applyTheme(b.dataset.theme)));
})();
