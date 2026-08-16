(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>\"']/g, (char) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    })[char]);
  }

  function renderMarkdown(source) {
    const raw = String(source ?? '');
    const blocks = [];
    let value = raw.replace(/```([\w-]+)?\n?([\s\S]*?)```/g, (_, language, code) => {
      const index = blocks.length;
      blocks.push(`<pre class="rich-code"><code>${escapeHtml(code.trimEnd())}</code></pre>`);
      return `\u0000CODE${index}\u0000`;
    });

    value = escapeHtml(value)
      .replace(/`([^`\n]+)`/g, '<code class="rich-inline-code">$1</code>')
      .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|\n)[ \t]*[-•][ \t]+(.+)/g, '$1<span class="rich-bullet">• $2</span>')
      .replace(/\n/g, '<br>');

    value = value.replace(/\u0000CODE(\d+)\u0000/g, (_, index) => blocks[Number(index)] || '');
    return value;
  }

  async function submitFeedback(rating) {
    try {
      await fetch('/feedback', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rating, text: ''})
      });
      window.dispatchEvent(new CustomEvent('teluai:toast', {detail: rating > 0 ? 'Thanks for the feedback.' : 'Feedback recorded.'}));
    } catch (_) {
      // Feedback is non-critical and must never interrupt a conversation.
    }
  }

  function addActions(row, value) {
    if (!row || row.classList.contains('user') || row.querySelector('.message-actions')) return;
    const actions = document.createElement('div');
    actions.className = 'message-actions';

    const copy = document.createElement('button');
    copy.type = 'button';
    copy.className = 'message-action';
    copy.setAttribute('aria-label', 'Copy response');
    copy.title = 'Copy response';
    copy.textContent = 'Copy';
    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(String(value ?? ''));
        copy.textContent = 'Copied';
        setTimeout(() => { copy.textContent = 'Copy'; }, 1400);
      } catch (_) {
        copy.textContent = 'Copy failed';
        setTimeout(() => { copy.textContent = 'Copy'; }, 1400);
      }
    });

    const up = document.createElement('button');
    up.type = 'button';
    up.className = 'message-action';
    up.setAttribute('aria-label', 'Good response');
    up.title = 'Helpful';
    up.textContent = 'Good';
    up.addEventListener('click', () => submitFeedback(5));

    const down = document.createElement('button');
    down.type = 'button';
    down.className = 'message-action';
    down.setAttribute('aria-label', 'Poor response');
    down.title = 'Not helpful';
    down.textContent = 'Not helpful';
    down.addEventListener('click', () => submitFeedback(1));

    actions.append(copy, up, down);
    row.appendChild(actions);
  }

  function enhanceExistingMessages() {
    document.querySelectorAll('#chat .message.assistant').forEach((row) => {
      const bubble = $('.bubble', row);
      if (!bubble || bubble.dataset.richRendered === '1') return;
      const value = bubble.textContent || '';
      bubble.innerHTML = renderMarkdown(value);
      bubble.dataset.richRendered = '1';
      addActions(row, value);
    });
  }

  const originalAddMessage = window.addMessage;
  if (typeof originalAddMessage === 'function') {
    window.addMessage = function enhancedAddMessage(value, role) {
      originalAddMessage(value, role);
      if (role === 'assistant') {
        const row = $('#chat .message:last-child');
        const bubble = $('.bubble', row);
        if (bubble) {
          bubble.innerHTML = renderMarkdown(value);
          bubble.dataset.richRendered = '1';
        }
        addActions(row, value);
      }
    };
  }

  const originalSend = window.send;
  if (typeof originalSend === 'function') {
    window.send = async function enhancedSend(value) {
      const button = $('#send');
      button?.classList.add('is-loading');
      button?.setAttribute('aria-busy', 'true');
      try {
        return await originalSend(value);
      } finally {
        button?.classList.remove('is-loading');
        button?.setAttribute('aria-busy', 'false');
      }
    };
  }

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      $('#input')?.focus();
    }
  });

  window.addEventListener('teluai:toast', (event) => {
    const text = event.detail;
    if (typeof window.toast === 'function' && text) window.toast(text);
  });

  const chat = $('#chat');
  if (chat) {
    chat.setAttribute('aria-live', 'polite');
    const observer = new MutationObserver(enhanceExistingMessages);
    observer.observe(chat, {childList: true});
  }

  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reducedMotion) document.documentElement.dataset.reducedMotion = 'true';
  enhanceExistingMessages();
})();
