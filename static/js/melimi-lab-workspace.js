(() => {
  const originalFetch = window.fetch.bind(window);
  const LAB_PREFIX = '[Melimi Lab] ';
  const sameOrigin = (url) => {
    try { return new URL(url, window.location.href).origin === window.location.origin; }
    catch { return false; }
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

  const refresh = async () => {
    if (window.__teluaiGenerating) return;
    const id = window.__teluaiConversationId;
    if (!id) return;
    try {
      const response = await originalFetch(`/conversations/${encodeURIComponent(id)}`, {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { 'X-TeluAI-Workspace': 'lab' },
      });
      if (!response.ok) return;
      const data = await response.json();
      if (Array.isArray(data.messages)) window.__teluaiRefreshConversation?.(data.messages);
    } catch {}
  };

  window.__teluaiLabRefresh = refresh;
  window.setInterval(refresh, 12000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
})();
