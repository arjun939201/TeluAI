(() => {
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    const response = await originalFetch(input, init);
    if (url.includes('/conversations') && response.ok && response.headers.get('content-type')?.includes('application/json')) {
      const data = await response.clone().json().catch(() => null);
      if (data && Array.isArray(data.conversations)) {
        data.conversations = data.conversations.filter(c => !String(c.title || '').startsWith('[Melimi Lab] '));
        return new Response(JSON.stringify(data), { status: response.status, headers: { 'Content-Type': 'application/json' } });
      }
    }
    return response;
  };

  // Put Melimi Telugu Lab inside the Main Chat menu/navigation, not as a
  // separate item floating below the sidebar navigation.
  const nav = document.querySelector('.nav');
  if (nav && !nav.querySelector('[data-melimi-lab-link]')) {
    const link = document.createElement('a');
    link.href = '/melimi-lab';
    link.dataset.melimiLabLink = 'true';
    link.textContent = '🔤 Melimi Telugu Lab';
    link.setAttribute('aria-label', 'Open Melimi Telugu Lab');
    link.title = 'Melimi Telugu Lab';
    link.style.display = 'flex';
    link.style.alignItems = 'center';
    link.style.width = '100%';
    link.style.boxSizing = 'border-box';
    link.style.padding = '10px 12px';
    link.style.textDecoration = 'none';
    link.style.fontWeight = '600';
    nav.appendChild(link);
  }
})();
