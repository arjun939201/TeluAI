(() => {
  const $ = s => document.querySelector(s);
  const pill = $('#engineStatus');
  if (!pill) return;

  const set = (state, label, details = '') => {
    pill.className = `engine-pill ${state}`;
    pill.querySelector('.engine-dot').setAttribute('aria-label', label);
    pill.querySelector('.engine-label').textContent = label;
    pill.querySelector('.engine-details').textContent = details;
  };

  const check = async () => {
    try {
      const response = await fetch('/health', {
        credentials: 'same-origin',
        cache: 'no-store',
      });
      const data = await response.json();
      if (!response.ok) throw new Error('Health check failed');
      set(
        'ready',
        'TeluAI Engine',
        `Online · ${data.vocabulary_entries ?? 0} language entries`,
      );
    } catch {
      set('error', 'Engine unavailable', 'Check the server');
    }
  };

  check();
  setInterval(check, 30000);
})();
