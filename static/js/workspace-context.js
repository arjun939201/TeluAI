(() => {
  const isLab = document.documentElement.dataset.page === 'melimi-lab';
  const workspace = isLab ? 'lab' : 'main';
  const originalFetch = window.fetch.bind(window);
  const storageKey = 'teluai-lab-conversation-ids-v1';
  const labCommands = ['/word','/content','/learn','/teach','/analyze','/generate','/grammar','/derive','/sandhi','/samasa','/parse','/refresh'];

  const readIds = () => {
    try { return new Set(JSON.parse(localStorage.getItem(storageKey) || '[]').map(String)); }
    catch { return new Set(); }
  };
  const writeIds = ids => {
    try { localStorage.setItem(storageKey, JSON.stringify([...ids])); } catch {}
  };
  const isLabCommand = text => {
    const value = String(text || '').trim().toLowerCase();
    return labCommands.some(command => value === command || value.startsWith(command + ' '));
  };
  const isChatRequest = url => url === '/chat' || url === '/chat/stream' || url.startsWith('/chat/');

  async function discoverLegacyLabIds(conversations) {
    const ids = readIds();
    const candidates = (conversations || []).filter(c => {
      const title = String(c.title || '').toLowerCase();
      return title.includes('melimi lab') || title.includes('linguistics lab') || !ids.has(String(c.id));
    }).slice(0, 40);
    await Promise.all(candidates.map(async c => {
      try {
        const response = await originalFetch('/conversations/' + encodeURIComponent(c.id), {
          credentials: 'same-origin',
          headers: { 'X-TeluAI-Workspace': 'lab' },
          cache: 'no-store'
        });
        if (!response.ok) return;
        const data = await response.json();
        if ((data.messages || []).some(m => m.role === 'user' && isLabCommand(m.content))) ids.add(String(c.id));
      } catch {}
    }));
    writeIds(ids);
    return ids;
  }

  window.teluaiWorkspace = workspace;
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    const headers = new Headers(init.headers || (typeof input !== 'string' ? input.headers : undefined));
    headers.set('X-TeluAI-Workspace', workspace);
    const options = { ...init, headers };

    if (isChatRequest(url) && typeof options.body === 'string') {
      try {
        const body = JSON.parse(options.body);
        const message = String(body.message || '').trim();
        if (!isLab && message.startsWith('/')) {
          if (url === '/chat/stream' || url.startsWith('/chat/')) {
            const stream = [
              'data: ' + JSON.stringify({ type: 'error', message: 'Melimi Lab commands are available only in the Melimi Telugu Lab.', code: 'workspace_boundary' }),
              'data: ' + JSON.stringify({ type: 'done' })
            ].join('\\n\\n') + '\\n\\n';
            return new Response(stream, { status: 200, headers: { 'Content-Type': 'text/event-stream' } });
          }
          return new Response(JSON.stringify({ detail: { message: 'Melimi Lab commands are available only in the Melimi Telugu Lab.', code: 'workspace_boundary' } }), {
            status: 403,
            headers: { 'Content-Type': 'application/json' }
          });
        }
        if (isLab) {
          body.mode = 'melimi';
          options.body = JSON.stringify(body);
        }
      } catch {}
    }

    const response = await originalFetch(input, options);
    if (url === '/conversations' && response.ok && response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.clone().json().catch(() => null);
      if (data && Array.isArray(data.conversations)) {
        const ids = await discoverLegacyLabIds(data.conversations);
        data.conversations = data.conversations.filter(c => isLab ? ids.has(String(c.id)) : !ids.has(String(c.id)));
        return new Response(JSON.stringify(data), { status: response.status, headers: { 'Content-Type': 'application/json' } });
      }
    }
    return response;
  };
})();
