(() => {
  const shell = document.querySelector('#appShell');
  const toggle = document.querySelector('#sidebarToggle');
  const focus = document.querySelector('#focusToggle');
  if (!shell) return;

  const key = 'teluai-workspace-v1';
  const read = () => { try { return JSON.parse(localStorage.getItem(key) || '{}'); } catch { return {}; } };
  const write = value => localStorage.setItem(key, JSON.stringify(value));
  const state = read();

  const setCollapsed = collapsed => {
    shell.classList.toggle('sidebar-collapsed', collapsed);
    toggle?.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    toggle?.setAttribute('title', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
    if (toggle) toggle.textContent = collapsed ? '›' : '‹';
  };
  const setFocus = enabled => {
    shell.classList.toggle('focus-mode', enabled);
    focus?.setAttribute('aria-pressed', String(enabled));
  };

  setCollapsed(state.sidebarCollapsed === true);
  setFocus(state.focusMode === true);

  toggle?.addEventListener('click', () => {
    const next = !shell.classList.contains('sidebar-collapsed');
    setCollapsed(next);
    const s = read(); s.sidebarCollapsed = next; write(s);
  });

  focus?.addEventListener('click', () => {
    const next = !shell.classList.contains('focus-mode');
    setFocus(next);
    const s = read(); s.focusMode = next; write(s);
  });

  // Keep the primary workspace usable when the browser becomes narrow.
  const media = matchMedia('(max-width: 820px)');
  const sync = () => { if (media.matches) setFocus(false); };
  media.addEventListener?.('change', sync);
})();
