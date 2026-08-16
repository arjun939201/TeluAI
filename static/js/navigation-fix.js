(() => {
  const $ = (s) => document.querySelector(s);

  // Keep navigation controls usable even when history/API loading fails.
  const openHistory = async () => {
    const modal = $('#history');
    const list = $('#historyList');
    if (!modal || !list) return;
    modal.classList.remove('hidden');
    closeMobileMenu?.();
    list.innerHTML = '<div class="empty-state">కతనాలు లోడవుతున్నాయి…</div>';
    try {
      if (!me) throw new Error('Account is not ready yet.');
      const d = await api('/conversations');
      const items = d.conversations || [];
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
    closeMobileMenu?.();
    closeAccountMenu?.();
    if (!me) {
      toast?.('Profile is still loading. Please try again.');
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

  const historyLink = $('#historyLink');
  const profileLink = $('#profileLink');
  const profileMenuItem = $('#profileMenuItem');

  if (historyLink) {
    historyLink.onclick = null;
    historyLink.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      openHistory();
    });
  }

  if (profileLink) {
    profileLink.onclick = null;
    profileLink.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleAccountMenu(event);
    });
  }

  if (profileMenuItem) {
    profileMenuItem.onclick = null;
    profileMenuItem.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      openProfileSafe();
    });
  }
})();
