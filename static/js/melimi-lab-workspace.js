(() => {
  const originalFetch = window.fetch.bind(window);
  const LAB_PREFIX = '[Melimi Lab] ';
  let activeConversationId = null;

  const sameOrigin = (url) => {
    try { return new URL(url, window.location.href).origin === window.location.origin; }
    catch { return false; }
  };

  const refreshVisibleConversation = () => {
    if (window.__teluaiGenerating) return;
    const input = document.querySelector('#input');
    if (input && (document.activeElement === input || input.value.trim())) return;
    const active = document.querySelector('.history-item.active');
    if (active) {
      activeConversationId = active.dataset.id || activeConversationId;
      active.click();
      return;
    }
    document.querySelector('#historyRefresh')?.click();
  };

  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    const headers = new Headers(init.headers || (typeof input !== 'string' ? input.headers : undefined));
    const options = { ...init, headers };
    if (sameOrigin(url)) {
      headers.set('X-TeluAI-Workspace', 'lab');
      if (typeof options.body === 'string' && (url.includes('/chat/') || url === '/chat')) {
        try {
          const body = JSON.parse(options.body);
          body.mode = 'melimi';
          options.body = JSON.stringify(body);
        } catch {}
      }
    }

    const response = await originalFetch(input, options);

    if (url.includes('/chat/stream') && response.ok) {
      response.clone().text().then(text => {
        for (const frame of text.split('\n\n')) {
          const line = frame.split('\n').find(x => x.startsWith('data:'));
          if (!line) continue;
          try {
            const event = JSON.parse(line.slice(5).trim());
            if (event.conversation_id) activeConversationId = event.conversation_id;
          } catch {}
        }
      }).catch(() => {});
    }

    if (response.ok && url.includes('/conversations') && response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.clone().json().catch(() => null);
      if (data && Array.isArray(data.conversations)) {
        data.conversations = data.conversations.filter(c => String(c.title || '').startsWith(LAB_PREFIX));
        return new Response(JSON.stringify(data), {
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
        });
      }
    }
    return response;
  };

  // The Lab always has an explicit Melimi mode even though the control is hidden.
  if (!document.querySelector('#modeSelect')) {
    const select = document.createElement('select');
    select.id = 'modeSelect';
    select.hidden = true;
    select.innerHTML = '<option value="melimi" selected>Melimi Telugu</option>';
    document.body.appendChild(select);
  }
  if (!document.querySelector('#preferredMode')) {
    const select = document.createElement('select');
    select.id = 'preferredMode';
    select.hidden = true;
    select.innerHTML = '<option value="melimi" selected>Melimi Telugu</option>';
    document.body.appendChild(select);
  }

  // Keep the Lab UI synchronized with database state without interrupting typing/generation.
  window.setInterval(refreshVisibleConversation, 15000);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refreshVisibleConversation();
  });

  // A successful command/message should settle into the persisted conversation immediately.
  const composer = document.querySelector('#composer');
  composer?.addEventListener('submit', () => window.setTimeout(refreshVisibleConversation, 900));
})();
