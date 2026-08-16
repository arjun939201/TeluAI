const $ = s => document.querySelector(s);
const api = async (url, options={}) => { const r = await fetch(url,{credentials:'same-origin',...options}); const d=await r.json().catch(()=>({})); if(!r.ok) throw Error(d.detail||'Request failed'); return d; };
let me=null, conversationId=null, messages=[], controller=null, generating=false, allConversations=[];
const uiKey='teluai-ui-v2';

function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#039;'}[c]));}
function toast(text){const x=document.createElement('div');x.className='toast';x.textContent=text;document.body.appendChild(x);setTimeout(()=>x.remove(),3000);}
function settingsLocal(){try{return JSON.parse(localStorage.getItem(uiKey)||'{}')}catch{return {}}}
function applyTheme(){const s=settingsLocal();let t=s.theme||'dark';if(t==='system')t=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=t;}
function openModal(id){$('#'+id)?.classList.remove('hidden');}
function closeModal(id){$('#'+id)?.classList.add('hidden');}

function markdown(text){
  const value=String(text??'');
  if(window.marked&&window.DOMPurify){
    marked.setOptions({gfm:true,breaks:true});
    return DOMPurify.sanitize(marked.parse(value),{USE_PROFILES:{html:true},ADD_ATTR:['target','rel','class','data-lang']});
  }
  return `<p>${esc(value).replace(/\n\n/g,'</p><p>').replace(/\n/g,'<br>')}</p>`;
}
function enhanceCode(container){
  container.querySelectorAll('pre').forEach(pre=>{
    const code=pre.querySelector('code'); if(!code)return;
    const cls=[...code.classList].find(x=>x.startsWith('language-')); const lang=cls?cls.slice(9):'';
    const bar=document.createElement('div');bar.className='code-bar';bar.innerHTML=`<span>${esc(lang||'code')}</span><button type="button">Copy</button>`;
    bar.querySelector('button').onclick=async()=>{try{await navigator.clipboard.writeText(code.textContent);bar.querySelector('button').textContent='Copied';setTimeout(()=>bar.querySelector('button').textContent='Copy',1400)}catch{toast('Could not copy code')}};
    pre.insertBefore(bar,code);
  });
}
function scrollBottom(){requestAnimationFrame(()=>$('#chatViewport').scrollTo({top:$('#chatViewport').scrollHeight,behavior:'smooth'}));}

function renderMessage(msg){
  const row=document.createElement('article');row.className=`message ${msg.role}`;row.dataset.id=msg.id||'';
  const body=document.createElement('div');body.className='message-body';
  if(msg.role==='assistant'){
    body.innerHTML=markdown(msg.content);enhanceCode(body);
  }else{
    const text=document.createElement('div');text.className='user-text';text.textContent=msg.content;body.appendChild(text);
  }
  row.appendChild(body);
  const actions=document.createElement('div');actions.className='message-actions';
  if(msg.role==='assistant'){
    actions.innerHTML='<button data-action="copy">Copy</button><button data-action="regenerate">Regenerate</button><button data-action="good" aria-label="Good response">👍</button><button data-action="bad" aria-label="Bad response">👎</button>';
  }else actions.innerHTML='<button data-action="edit">Edit</button>';
  actions.querySelectorAll('button').forEach(b=>b.onclick=()=>messageAction(msg,b.dataset.action));
  row.appendChild(actions);$('#chat').appendChild(row);return row;
}
function renderAll(){const chat=$('#chat');chat.innerHTML='';messages.forEach(renderMessage);$('#welcome').classList.toggle('hidden',messages.length>0);scrollBottom();}

async function feedback(msg,rating){try{await api('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message_id:msg.id,rating})});toast('Thanks for the feedback');}catch{toast('Feedback could not be saved');}}
async function messageAction(msg,action){
  if(action==='copy'){try{await navigator.clipboard.writeText(msg.content);toast('Copied');}catch{toast('Could not copy')}}
  else if(action==='good')await feedback(msg,5);
  else if(action==='bad')await feedback(msg,1);
  else if(action==='regenerate'){if(!msg.id||!conversationId)return;await regenerate(msg.id);}
  else if(action==='edit'){await editMessage(msg);}
}
async function editMessage(msg){
  const row=document.querySelector(`.message[data-id="${CSS.escape(String(msg.id))}"]`);if(!row)return;
  const editor=document.createElement('div');editor.className='edit-box';editor.innerHTML=`<textarea>${esc(msg.content)}</textarea><div><button class="secondary">Cancel</button><button class="primary">Save & resend</button></div>`;
  row.querySelector('.message-body').replaceChildren(editor);const ta=editor.querySelector('textarea');ta.focus();ta.setSelectionRange(ta.value.length,ta.value.length);
  editor.querySelector('.secondary').onclick=renderAll;
  editor.querySelector('.primary').onclick=async()=>{const content=ta.value.trim();if(!content)return;try{await api(`/messages/${msg.id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({content})});await loadConversation(conversationId);const userMsg=messages.find(x=>x.id===msg.id);if(userMsg)await regenerate(userMsg.id);}catch(e){toast(e.message)}};
}

async function regenerate(messageId){
  if(generating)return;generating=true;controller=new AbortController();setGenerating(true);
  const old=messages.find(m=>m.id===messageId);if(old&&old.role==='assistant'){messages=messages.filter(m=>m.id!==messageId);renderAll();}
  const row={role:'assistant',content:'',id:null,streaming:true};messages.push(row);const el=renderMessage(row);const body=el.querySelector('.message-body');
  try{await consumeStream(`/chat/${encodeURIComponent(conversationId)}/regenerate`,{message_id:messageId,mode:$('#modeSelect').value,response_length:currentLength() },body,row);}
  finally{generating=false;controller=null;setGenerating(false);await loadConversation(conversationId);}
}
function currentLength(){return window.chatResponseLength||'normal';}

async function sendMessage(){
  if(generating)return;const input=$('#input');const text=input.value.trim();if(!text)return;
  const mode=$('#modeSelect').value;const user={role:'user',content:text,id:null};messages.push(user);renderAll();input.value='';resize();
  generating=true;controller=new AbortController();setGenerating(true);
  const assistant={role:'assistant',content:'',id:null,streaming:true};messages.push(assistant);const el=renderMessage(assistant);const body=el.querySelector('.message-body');
  try{await consumeStream('/chat/stream',{message:text,mode,conversation_id:conversationId,response_length:currentLength()},body,assistant);}
  catch(e){if(e.name!=='AbortError')toast(e.message||'Could not reach the AI service');}
  finally{generating=false;controller=null;setGenerating(false);if(conversationId)await loadConversation(conversationId);else await loadHistory();}
}

async function consumeStream(url,payload,body,assistant){
  const response=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'text/event-stream'},body:JSON.stringify(payload),signal:controller?.signal});
  if(!response.ok){const d=await response.json().catch(()=>({}));throw Error(d.detail||'Request failed');}
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
  while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});const frames=buffer.split('\n\n');buffer=frames.pop()||'';for(const frame of frames){const line=frame.split('\n').find(x=>x.startsWith('data:'));if(!line)continue;let event;try{event=JSON.parse(line.slice(5).trim())}catch{continue}
      if(event.type==='start'){conversationId=event.conversation_id||conversationId;assistant.mode=event.mode;$('#generationStatus').textContent='Generating…';}
      else if(event.type==='delta'){assistant.content+=event.text;body.innerHTML=markdown(assistant.content);enhanceCode(body);scrollBottom();}
      else if(event.type==='error'){throw Error(event.message||'Generation failed');}
      else if(event.type==='done'){assistant.id=event.message_id||assistant.id;assistant.streaming=false;$('#generationStatus').textContent='';}
    }}
}
function setGenerating(value){$('#send').textContent=value?'■':'↑';$('#send').classList.toggle('stop',value);$('#input').disabled=false;$('#generationStatus').textContent=value?'Generating…':'';}
$('#composer').addEventListener('submit',e=>{e.preventDefault();if(generating){controller?.abort();generating=false;setGenerating(false);return}sendMessage();});
$('#input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(generating){controller?.abort();generating=false;setGenerating(false)}else sendMessage();}});
$('#input').addEventListener('input',resize);function resize(){const x=$('#input');x.style.height='auto';x.style.height=Math.min(x.scrollHeight,180)+'px';}
document.querySelectorAll('.suggestions button').forEach(b=>b.onclick=()=>{$('#input').value=b.dataset.message;resize();sendMessage();});

async function loadHistory(){try{const d=await api('/conversations');allConversations=d.conversations||[];renderHistory();}catch{}}
function renderHistory(){const q=$('#historySearch').value.trim().toLowerCase();let list=[...allConversations];const sort=$('#historySort').value;if(sort==='oldest')list.sort((a,b)=>String(a.created_at).localeCompare(String(b.created_at)));else if(sort==='title')list.sort((a,b)=>String(a.title).localeCompare(String(b.title)));else list.sort((a,b)=>String(b.updated_at).localeCompare(String(a.updated_at)));if(q)list=list.filter(x=>String(x.title).toLowerCase().includes(q));$('#historyList').innerHTML=list.slice(0,40).map(c=>`<button class="history-item ${c.id===conversationId?'active':''}" data-id="${esc(c.id)}"><strong>${esc(c.title||'New chat')}</strong><span>${esc(new Date(c.updated_at).toLocaleDateString())}</span></button>`).join('')||'<div class="history-empty">No chats yet</div>';document.querySelectorAll('.history-item').forEach(x=>x.onclick=()=>loadConversation(x.dataset.id));}
async function loadConversation(id){try{const d=await api('/conversations/'+encodeURIComponent(id));conversationId=id;messages=(d.messages||[]).map(x=>({id:x.id,role:x.role,content:x.content}));renderAll();renderHistory();closeMobile();}catch(e){toast(e.message)}}
function newChat(){conversationId=null;messages=[];renderAll();renderHistory();$('#input').focus();closeMobile();}
$('#newChat').onclick=newChat;$('#historyRefresh').onclick=loadHistory;$('#historySearch').oninput=renderHistory;$('#historySort').onchange=renderHistory;

function closeMobile(){const s=$('#sidebar');s.classList.remove('open');$('#mobileBackdrop').classList.add('hidden');}
$('#mobileMenu').onclick=()=>{$('#sidebar').classList.add('open');$('#mobileBackdrop').classList.remove('hidden')};$('#mobileBackdrop').onclick=closeMobile;

async function loadSettings(){try{const d=await api('/me/settings');$('#preferredMode').value=d.preferred_mode||'auto';$('#modeSelect').value=d.preferred_mode||'auto';window.chatResponseLength=d.response_length||'normal';$('#responseLength').value=window.chatResponseLength;$('#memoryEnabled').checked=d.memory_enabled!==false;}catch{}}
$('#settingsButton').onclick=async()=>{await loadSettings();openModal('settings');};
$('#saveSettings').onclick=async()=>{try{const mode=$('#preferredMode').value;const len=$('#responseLength').value;window.chatResponseLength=len;await api('/me/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({preferred_mode:mode,response_length:len,memory_enabled:$('#memoryEnabled').checked})});const local=settingsLocal();local.theme=$('#theme').value;localStorage.setItem(uiKey,JSON.stringify(local));applyTheme();$('#modeSelect').value=mode;closeModal('settings');toast('Settings saved');}catch(e){$('#settingsStatus').textContent=e.message}};
$('#modeSelect').onchange=()=>{};$('#theme').value=settingsLocal().theme||'dark';$('#theme').onchange=()=>{const s=settingsLocal();s.theme=$('#theme').value;localStorage.setItem(uiKey,JSON.stringify(s));applyTheme();};document.querySelectorAll('[data-close]').forEach(x=>x.onclick=()=>closeModal(x.dataset.close));
$('#logoutButton').onclick=async()=>{try{await api('/auth/logout',{method:'POST'})}finally{location.reload()}};

function showAuth(mode){['guest','login','register'].forEach(x=>{$('#'+x+'Form').classList.toggle('hidden',x!==mode);$('#'+x+'Tab').classList.toggle('active',x===mode)});openModal('auth');}
$('#guestTab').onclick=()=>showAuth('guest');$('#loginTab').onclick=()=>showAuth('login');$('#registerTab').onclick=()=>showAuth('register');
async function authSubmit(kind,form,endpoint,payload,errorId){form.onsubmit=async e=>{e.preventDefault();try{await api(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())});location.reload();}catch(x){$('#'+errorId).textContent=x.message}}}
authSubmit('guest',$('#guestForm'),'/auth/guest',()=>({username:$('#guestUser').value.trim(),password:$('#guestPass').value}), 'guestError');
authSubmit('login',$('#loginForm'),'/auth/login',()=>({identifier:$('#loginIdentifier').value.trim(),password:$('#loginPass').value}),'loginError');
authSubmit('register',$('#registerForm'),'/auth/register',()=>({username:$('#regUser').value.trim(),email:$('#regEmail').value.trim(),password:$('#regPass').value}),'registerError');

async function loadMe(){try{me=await api('/auth/me');$('#accountName').textContent=me.username;$('#accountRole').textContent=me.role;$('#avatar').textContent=(me.username||'T').slice(0,1).toUpperCase();if(['admin','owner'].includes(me.role))$('#adminButton').classList.remove('hidden');$('#auth').classList.add('hidden');await loadSettings();await loadHistory();}catch{showAuth('guest');}}
$('#adminButton').onclick=()=>location.href='/admin';
applyTheme();resize();loadMe();
