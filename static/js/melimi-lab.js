(() => {
  const input = document.querySelector('#input');
  const refresh = document.querySelector('#labRefresh');
  if (!input) return;

  const resize = () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 180) + 'px';
  };

  document.querySelectorAll('[data-lab-command]').forEach(button => {
    button.addEventListener('click', () => {
      input.value = button.dataset.labCommand || '';
      input.focus();
      resize();
    });
  });

  // Lab refresh uses the existing shared Melimi refresh implementation.
  refresh?.addEventListener('click', async () => {
    if (typeof window.refreshMelimiKnowledge === 'function') {
      await window.refreshMelimiKnowledge({ includeChats: true });
    } else {
      window.location.reload();
    }
  });
})();
