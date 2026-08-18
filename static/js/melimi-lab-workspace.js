(() => {
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    const headers = new Headers(init.headers || (typeof input !== 'string' ? input.headers : undefined));
    const options = { ...init, headers };
    if (url.includes('/chat/stream') || url === '/chat' || url.includes('/chat/')) {
      headers.set('X-TeluAI-Workspace', 'lab');
      if (typeof options.body === 'string') {
        try {
          const body = JSON.parse(options.body);
          body.mode = 'melimi';
          options.body = JSON.stringify(body);
        } catch {}
      }
    }
    const response = await originalFetch(input, options);
    if (url.includes('/conversations') && response.ok && response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.clone().json().catch(() => null);
      if (data && Array.isArray(data.conversations)) {
        data.conversations = data.conversations.filter(c => String(c.title || '').startsWith('[Melimi Lab] '));
        return new Response(JSON.stringify(data), { status: response.status, headers: { 'Content-Type': 'application/json' } });
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
})();
