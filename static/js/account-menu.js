(() => {
  const account = document.querySelector('.account');
  const sidebar = document.querySelector('.lab-sidebar, .sidebar');
  if (!account || !sidebar) return;

  const actionIds = ['settingsButton', 'adminButton', 'logoutButton'];
  const actions = actionIds.map(id => document.getElementById(id)).filter(Boolean);
  if (!actions.length) return;

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'account account-trigger';
  trigger.setAttribute('aria-haspopup', 'menu');
  trigger.setAttribute('aria-expanded', 'false');
  trigger.innerHTML = account.innerHTML + '<span class="account-chevron" aria-hidden="true">⌃</span>';
  account.replaceWith(trigger);

  const menu = document.createElement('div');
  menu.className = 'account-menu hidden';
  menu.setAttribute('role', 'menu');
  menu.innerHTML = '<div class="account-menu-header"><strong id="accountMenuName">Account</strong><span id="accountMenuRole">Owner</span></div>';
  actions.forEach(action => {
    action.classList.add('account-menu-item');
    action.setAttribute('role', 'menuitem');
    menu.appendChild(action);
  });
  sidebar.appendChild(menu);

  const syncIdentity = () => {
    const name = document.getElementById('accountName');
    const role = document.getElementById('accountRole');
    const menuName = document.getElementById('accountMenuName');
    const menuRole = document.getElementById('accountMenuRole');
    if (name && menuName) menuName.textContent = name.textContent || 'Account';
    if (role && menuRole) menuRole.textContent = role.textContent || '';
  };

  const setOpen = open => {
    menu.classList.toggle('hidden', !open);
    trigger.setAttribute('aria-expanded', String(open));
    trigger.classList.toggle('is-open', open);
    if (open) syncIdentity();
  };

  trigger.addEventListener('click', event => {
    event.stopPropagation();
    setOpen(menu.classList.contains('hidden'));
  });
  document.addEventListener('click', event => {
    if (!menu.contains(event.target) && !trigger.contains(event.target)) setOpen(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') setOpen(false);
  });

  new MutationObserver(syncIdentity).observe(trigger, { subtree: true, childList: true, characterData: true });
})();
