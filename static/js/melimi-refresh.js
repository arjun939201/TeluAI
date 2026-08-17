/* Live Melimi knowledge refresh: keeps the current conversation open. */
(function(){
  function install(){
    const topbar=document.querySelector('.topbar');
    if(!topbar || document.getElementById('melimiRefresh')) return;
    const button=document.createElement('button');
    button.id='melimiRefresh';
    button.type='button';
    button.className='icon-button';
    button.setAttribute('aria-label','Refresh Melimi knowledge');
    button.title='Refresh Melimi knowledge';
    button.textContent='↻';
    button.addEventListener('click',async()=>{
      if(button.disabled) return;
      button.disabled=true;
      button.classList.add('spinning');
      try{
        /* Reload the active conversation in place. The current conversation id
           is preserved; newly learned MASTER knowledge is therefore available
           to the next message without navigating away from the chat. */
        if(typeof conversationId!=='undefined' && conversationId && typeof loadConversation==='function'){
          await loadConversation(conversationId);
        }
        if(typeof loadHistory==='function') await loadHistory();
        if(typeof toast==='function') toast('Melimi knowledge refreshed');
      }catch(e){
        if(typeof toast==='function') toast('Could not refresh Melimi knowledge');
      }finally{
        button.disabled=false;
        button.classList.remove('spinning');
      }
    });
    const spacer=topbar.querySelector('.topbar-spacer');
    if(spacer) spacer.before(button); else topbar.appendChild(button);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',install,{once:true});
  else install();
})();
