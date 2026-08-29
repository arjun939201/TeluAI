(() => {
  const originalFetch = window.fetch.bind(window);

  // The main workspace owns only main-chat history. Lab conversations remain
  // available inside the Lab workspace and are never mixed into this list.
  window.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    const response = await originalFetch(input, init);

    if (
      url.includes('/conversations') &&
      response.ok &&
      response.headers.get('content-type')?.includes('application/json')
    ) {
      const data = await response.clone().json().catch(() => null);
      if (data && Array.isArray(data.conversations)) {
        data.conversations = data.conversations.filter(
          conversation => !String(conversation.title || '').startsWith('[Melimi Lab] '),
        );
        return new Response(JSON.stringify(data), {
          status: response.status,
          statusText: response.statusText,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    return response;
  };
})();
