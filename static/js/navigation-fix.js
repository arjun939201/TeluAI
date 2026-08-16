(() => {
  const $ = (s) => document.querySelector(s);
  const bind = (selector, event, handler) => {
    const node = $(selector);
    if (!node) return;
    node.addEventListener(event, handler);
  };

  const openHistory = async () => {
    const modal = $('#history');
    const list = $('#historyList');
    if (!modal || !list) return;
    modal.classList.remove('hidden');
    if (typeof closeMobileMenu === 'function') closeMobileMenu();
    list.innerHTML = '<div class="empty-state">కతనాలు లోడవుతున్నాయి…</div>';
    try {
      if (!me) throw new Error('Account is not ready yet.');
      const data = await api('/conversations');
      const items = data.conversations || [];
      list.innerHTML = items.length
        ? items.map(c => `<button type="button" class="history-item" data-id="${esc(c.id || c.conversation_id)}"><b>${esc(c.title || c.name || 'Conversation')}</b><span>${esc(c.updated_at || c.created_at || '')}</span></button>`).join('')
        : '<div class="empty-state">కతనాలు లేవు.</div>';
      list.querySelectorAll('.history-item').forEach(button => {
        button.addEventListener('click', () => openConversation(button.dataset.id));
      });
    } catch (error) {
      list.innerHTML = `<div class="empty-state">కతనాలు లోడ్ కాలేదు.<br><small>${esc(error.message)}</small></div>`;
    }
  };

  const openProfileSafe = () => {
    const modal = $('#profile');
    if (!modal) return;
    if (typeof closeMobileMenu === 'function') closeMobileMenu();
    if (typeof closeAccountMenu === 'function') closeAccountMenu();
    if (!me) {
      if (typeof toast === 'function') toast('Profile is still loading. Please try again.');
      return;
    }
    $('#profileName').value = me.username || '';
    $('#profileEmail').value = me.role === 'guest' ? 'Not linked — Guest account' : (me.email || '');
    $('#profileEmailWrap').style.display = me.role === 'guest' ? 'none' : '';
    $('#profileRole').value = me.role === 'guest' ? 'GUEST' : String(me.role || 'ACCOUNT').toUpperCase();
    $('#newUsername').value = '';
    $('#newPassword').value = '';
    $('#currentPassword').value = '';
    $('#credentialStatus').textContent = '';
    modal.classList.remove('hidden');
  };

  // The legacy professional.js contains an optional #assistantLink reference.
  // Bind the rest of the application independently so one missing optional
  // element can never disable settings, auth, history, or profile controls.
  bind('#mobileMenu', 'click', () => toggleMobileMenu());
  bind('#mobileBackdrop', 'click', () => closeMobileMenu());
  bind('#newChat', 'click', () => resetChat());
  bind('#historyLink', 'click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    openHistory();
  });
  bind('#profileLink', 'click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    toggleAccountMenu(event);
  });
  bind('#profileMenuItem', 'click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    openProfileSafe();
  });
  bind('#settingsLink', 'click', () => openSettings());
  bind('#adminLink', 'click', () => {
    closeAccountMenu();
    closeMobileMenu();
    location.href = '/admin';
  });
  bind('#logout', 'click', () => logout());
  bind('#send', 'click', () => send($('#input').value.trim()));
  bind('#input', 'keydown', (event) => {
    if (event.key === 'Escape') {
      closeModal('#settings');
      closeModal('#profile');
      closeModal('#history');
      closeAccountMenu();
      closeMobileMenu();
    }
  });
  bind('#closeSettings', 'click', () => closeModal('#settings'));
  bind('#closeProfile', 'click', () => closeModal('#profile'));
  bind('#closeHistory', 'click', () => closeModal('#history'));
  bind('#saveSettings', 'click', () => saveSettings());
  bind('#resetSettings', 'click', () => resetSettings());
  bind('#saveCredentials', 'click', () => saveCredentials());
  document.querySelectorAll('[data-theme]').forEach(button => {
    button.addEventListener('click', () => applyTheme(button.dataset.theme));
  });
  document.querySelectorAll('.suggestion').forEach(button => {
    button.addEventListener('click', () => send(button.dataset.message || ''));
  });

  const clearAuth = () => {
    if (typeof clearAuthErrors === 'function') clearAuthErrors();
  };
  bind('#guestTab', 'click', () => { clearAuth(); showAuth('guest'); });
  bind('#loginTab', 'click', () => { clearAuth(); showAuth('login'); });
  bind('#registerTab', 'click', () => { clearAuth(); showAuth('register'); });
  bind('#toRegister', 'click', () => showAuth('register'));
  bind('#toGuest', 'click', () => showAuth('guest'));

  bind('#guestForm', 'submit', async (event) => {
    event.preventDefault();
    clearAuth();
    try {
      await api('/auth/guest', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:$('#guestUser').value.trim(), password:$('#guestPass').value})});
      location.reload();
    } catch (error) { $('#guestError').textContent = error.message; }
  });
  bind('#loginForm', 'submit', async (event) => {
    event.preventDefault();
    clearAuth();
    try {
      await api('/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identifier:$('#loginIdentifier').value.trim(), password:$('#loginPass').value})});
      location.reload();
    } catch (error) { $('#loginError').textContent = error.message; }
  });
  bind('#registerForm', 'submit', async (event) => {
    event.preventDefault();
    clearAuth();
    try {
      await api('/auth/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:$('#regUser').value.trim(), email:$('#regEmail').value.trim(), password:$('#regPass').value})});
      location.reload();
    } catch (error) { $('#registerError').textContent = error.message; }
  });
})();
