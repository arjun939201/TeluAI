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

  const sidebar = document.querySelector('#sidebar');
  if (sidebar && !document.querySelector('[data-melimi-lab-link]')) {
    const link = document.createElement('a');
    link.href = '/melimi-lab';
    link.dataset.melimiLabLink = 'true';
    link.textContent = '🔤 Melimi Telugu Lab';
    link.setAttribute('aria-label', 'Open Melimi Telugu Lab');
    link.style.display = 'block';
    link.style.margin = '10px 16px';
    link.style.padding = '10px 12px';
    link.style.borderRadius = '10px';
    link.style.textDecoration = 'none';
    link.style.fontWeight = '600';
    sidebar.querySelector('.sidebar-spacer')?.before(link);
  }
})();
