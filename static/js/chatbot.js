const chatContainer=document.getElementById("chatContainer");
const welcome=document.getElementById("welcome");
const chatForm=document.getElementById("chatForm");
const messageInput=document.getElementById("messageInput");
const sendButton=document.getElementById("sendButton");
const clearButton=document.getElementById("clearButton");
const mobileNewChat=document.getElementById("mobileNewChat");
const mobileHistoryButton=document.getElementById("mobileHistoryButton");
const mobileSidebarBackdrop=document.getElementById("mobileSidebarBackdrop");
const sidebar=document.querySelector(".sidebar");
const modelName=document.getElementById("modelName");
const authGate=document.getElementById("authGate");
const authForm=document.getElementById("authForm");
const authUsername=document.getElementById("authUsername");
const authEmail=document.getElementById("authEmail");
const authPassword=document.getElementById("authPassword");
const authSubmit=document.getElementById("authSubmit");
const authError=document.getElementById("authError");
const loginTab=document.getElementById("loginTab");
const registerTab=document.getElementById("registerTab");
const forgotPasswordButton=document.getElementById("forgotPasswordButton"),forgotPasswordModal=document.getElementById("forgotPasswordModal"),forgotPasswordForm=document.getElementById("forgotPasswordForm"),forgotPasswordEmail=document.getElementById("forgotPasswordEmail"),forgotPasswordResult=document.getElementById("forgotPasswordResult"),closeForgotPassword=document.getElementById("closeForgotPassword");
const accountName=document.getElementById("accountName");
const logoutButton=document.getElementById("logoutButton");

let mode="melimi",history=[],isSending=false,currentConversationId=null,authMode="login";

function setMode(newMode="melimi"){mode="melimi";if(modelName)modelName.textContent="మేలిమి తెలుగు AI";if(messageInput)messageInput.placeholder="మేలిమి తెలుగులో అడుగు..."}
function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
function renderMelimiText(text,audit){const map=new Map((audit||[]).map(x=>[x.word,x]));return String(text).split(/([\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*)/g).map(part=>{const x=map.get(part);if(!x)return escapeHtml(part);const cls=x.clickable?"word-token unregistered":"word-token";const title=x.loan?"Loan/foreign word — click to teach Melimi":(x.melimi_gap?"Melimi equivalent needed — click to teach":"Melimi word");return `<span class="${cls}" data-word="${escapeHtml(part)}" title="${title}">${escapeHtml(part)}</span>`}).join("")}
function addMessage(text,role,melimi=false,audit=[]){const wrapper=document.createElement("div");wrapper.className=`message ${role}`;if(role==="assistant"&&melimi)wrapper.classList.add("melimi");const content=document.createElement("div");content.className="message-content";content.innerHTML=role==="assistant"&&melimi?renderMelimiText(text,audit):escapeHtml(text);wrapper.appendChild(content);chatContainer.appendChild(wrapper);scrollToBottom()}
function showTyping(){const wrapper=document.createElement("div");wrapper.id="typingIndicator";wrapper.className="typing-message";wrapper.innerHTML='<div class="typing"><span></span><span></span><span></span></div>';chatContainer.appendChild(wrapper);scrollToBottom()}
function removeTyping(){document.getElementById("typingIndicator")?.remove()}
function addError(text){const wrapper=document.createElement("div");wrapper.className="error-message";const error=document.createElement("div");error.className="error";error.textContent=text;wrapper.appendChild(error);chatContainer.appendChild(wrapper);scrollToBottom()}
function scrollToBottom(){requestAnimationFrame(()=>chatContainer.scrollTop=chatContainer.scrollHeight)}
function resizeInput(){messageInput.style.height="auto";messageInput.style.height=`${Math.min(messageInput.scrollHeight,160)}px`}
messageInput.addEventListener("input",resizeInput);

async function sendMessage(){
 if(isSending)return;const text=messageInput.value.trim();if(!text)return;
 isSending=true;sendButton.disabled=true;messageInput.value="";resizeInput();if(welcome)welcome.style.display="none";addMessage(text,"user");const previousHistory=[...history];showTyping();
 try{const response=await fetch("/chat",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text,mode,history:previousHistory,conversation_id:currentConversationId})});const data=await response.json().catch(()=>({}));removeTyping();if(!response.ok){addError(data.detail||`Server error: ${response.status}`);return}if(!data.reply){addError("AI returned no response.");return}currentConversationId=data.conversation_id||currentConversationId;addMessage(data.reply,"assistant",mode==="melimi",data.word_audit||[]);history.push({role:"user",content:text});history.push({role:"assistant",content:data.reply});loadConversations();}
 catch(error){removeTyping();console.error(error);addError("Could not reach the server. Please try again.")}finally{isSending=false;sendButton.disabled=false;messageInput.focus()}
}
chatForm.addEventListener("submit",e=>{e.preventDefault();sendMessage()});messageInput.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage()}});
document.querySelectorAll(".suggestion").forEach(button=>button.addEventListener("click",()=>{const text=button.dataset.message;if(!text)return;messageInput.value=text;resizeInput();sendMessage()}));
function closeMobileSidebar(){
  sidebar?.classList.remove("mobile-open");
  mobileSidebarBackdrop?.classList.add("hidden");
  mobileHistoryButton?.setAttribute("aria-expanded","false");
}
function openMobileSidebar(){
  sidebar?.classList.add("mobile-open");
  mobileSidebarBackdrop?.classList.remove("hidden");
  mobileHistoryButton?.setAttribute("aria-expanded","true");
}
function newChat(){history=[];currentConversationId=null;chatContainer.querySelectorAll(".message,.error-message,.typing-message").forEach(x=>x.remove());if(welcome)welcome.style.display="";messageInput.value="";resizeInput();closeMobileSidebar();messageInput.focus()}
clearButton.addEventListener("click",newChat);mobileNewChat.addEventListener("click",newChat);mobileHistoryButton?.addEventListener("click",()=>sidebar?.classList.contains("mobile-open")?closeMobileSidebar():openMobileSidebar());mobileSidebarBackdrop?.addEventListener("click",closeMobileSidebar);

function setAuthMode(next){authMode=next;const reg=next==="register";loginTab.classList.toggle("active",!reg);registerTab.classList.toggle("active",reg);authUsername.classList.toggle("hidden",!reg);authUsername.required=reg;authEmail.placeholder=reg?"Email":"Email or username";authSubmit.textContent=reg?"Register":"Login";authError.textContent=""}
loginTab.addEventListener("click",()=>setAuthMode("login"));registerTab.addEventListener("click",()=>setAuthMode("register"));
forgotPasswordButton?.addEventListener("click",e=>{if(forgotPasswordModal){e.preventDefault();forgotPasswordModal.classList.remove("hidden");forgotPasswordResult.textContent="";forgotPasswordEmail?.focus()}});closeForgotPassword?.addEventListener("click",()=>forgotPasswordModal?.classList.add("hidden"));forgotPasswordModal?.addEventListener("click",e=>{if(e.target===forgotPasswordModal)forgotPasswordModal.classList.add("hidden")});forgotPasswordForm?.addEventListener("submit",async e=>{e.preventDefault();forgotPasswordResult.textContent="Sending…";try{const r=await fetch("/auth/forgot-password",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:forgotPasswordEmail.value.trim()})});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||"Could not request password reset");forgotPasswordResult.style.color="#8ed9a0";forgotPasswordResult.textContent=d.message||"If the account exists, a reset link has been sent."}catch(e){forgotPasswordResult.style.color="#ef7777";forgotPasswordResult.textContent=e.message||"Could not request password reset."}});

document.querySelectorAll(".password-toggle[data-password-target]").forEach(button=>{
  button.addEventListener("click",()=>{
    const input=document.getElementById(button.dataset.passwordTarget);
    if(!input)return;
    const visible=input.type==="text";
    input.type=visible?"password":"text";
    button.textContent=visible?"Show":"Hide";
    button.setAttribute("aria-label",visible?"Show password":"Hide password");
    button.setAttribute("aria-pressed",String(!visible));
  });
});

async function checkAuth(){try{const r=await fetch("/auth/me",{credentials:"same-origin"});if(!r.ok)throw Error();const d=await r.json();enterApp(d)}catch(e){authGate.classList.remove("hidden");messageInput.disabled=true;sendButton.disabled=true}}
function enterApp(user){authGate.classList.add("hidden");messageInput.disabled=false;sendButton.disabled=false;accountName.textContent=user.username;loadConversations();messageInput.focus()}
authForm.addEventListener("submit",async e=>{e.preventDefault();authError.textContent="";authSubmit.disabled=true;try{const url=authMode==="register"?"/auth/register":"/auth/login";const body=authMode==="register"?{username:authUsername.value.trim(),email:authEmail.value.trim(),password:authPassword.value}:{identifier:authEmail.value.trim(),password:authPassword.value};const r=await fetch(url,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||"Authentication failed");authForm.reset();enterApp(d)}catch(e){authError.textContent=e.message}finally{authSubmit.disabled=false}});
logoutButton.addEventListener("click",async()=>{await fetch("/auth/logout",{method:"POST",credentials:"same-origin"});location.reload()});

async function loadConversations(){try{const r=await fetch("/conversations",{credentials:"same-origin"});if(!r.ok)return;const d=await r.json();const box=document.getElementById("chatHistory");box.innerHTML="";if(!(d.conversations||[]).length){const empty=document.createElement("div");empty.className="history-empty";empty.textContent="No chats yet";box.appendChild(empty)}(d.conversations||[]).forEach(c=>{const item=document.createElement("div");item.className="chat-item"+(c.id===currentConversationId?" active":"");item.innerHTML=`<span class="chat-icon">◌</span><span>${escapeHtml(c.title||"New chat")}</span>`;item.addEventListener("click",()=>loadConversation(c.id));box.appendChild(item)})}catch(e){}}
async function loadConversation(id){try{const r=await fetch(`/conversations/${encodeURIComponent(id)}`,{credentials:"same-origin"});if(!r.ok)return;const d=await r.json();currentConversationId=id;history=[];chatContainer.querySelectorAll(".message,.error-message,.typing-message").forEach(x=>x.remove());if(welcome)welcome.style.display="none";(d.messages||[]).forEach(m=>{addMessage(m.content,m.role,m.role==="assistant"&&mode==="melimi",[]);history.push({role:m.role,content:m.content})});loadConversations();closeMobileSidebar()}catch(e){addError("Could not load this conversation.")}}

function modalElements(){return {modal:document.getElementById("wordModal"),word:document.getElementById("selectedWord"),status:document.getElementById("wordStatus"),root:document.getElementById("wordRoot"),meaning:document.getElementById("wordMeaning"),pos:document.getElementById("wordPos"),melimi:document.getElementById("wordMelimi"),formation:document.getElementById("wordFormation"),result:document.getElementById("wordResult"),register:document.getElementById("registerWord")}}
function closeWordModal(){const x=modalElements();x.modal?.classList.add("hidden")}
async function openWordModal(word=""){const x=modalElements();if(!x.modal)return;x.word.textContent=word||"కొత్త మేలిమి పదం";x.root.value=word||"";x.meaning.value="";x.pos.value="";x.melimi.value="";x.formation.value="";x.result.textContent="";x.register.disabled=false;x.status.textContent=word?"Enter the verified Melimi Telugu form.":"Add a user-verified Melimi Telugu word.";x.modal.classList.remove("hidden");if(word){try{const r=await fetch("/melimi/word/"+encodeURIComponent(word));const d=await r.json();if(d.melimi_equivalent)x.melimi.value=d.melimi_equivalent;if(d.root_candidate)x.root.value=d.root_candidate}catch(e){}}setTimeout(()=>x.melimi.focus(),50)}
document.addEventListener("click",e=>{
  const token=e.target.closest?.(".word-token.unregistered");
  if(token){e.preventDefault();e.stopPropagation();openWordModal(token.dataset.word||token.textContent.trim())}
});
document.getElementById("closeWordModal")?.addEventListener("click",(e)=>{e.preventDefault();closeWordModal()});
document.getElementById("cancelWord")?.addEventListener("click",(e)=>{e.preventDefault();closeWordModal()});
document.getElementById("wordModalBackdrop")?.addEventListener("click",closeWordModal);
document.addEventListener("keydown",e=>{if(e.key==="Escape" && !document.getElementById("wordModal")?.classList.contains("hidden"))closeWordModal()});
document.getElementById("registerWord")?.addEventListener("click",async()=>{const x=modalElements();const source=x.root.value.trim()||x.word.textContent.trim();const melimi=x.melimi.value.trim();if(!source||!melimi){x.result.style.color="#ef7777";x.result.textContent="Enter both source and Melimi word.";return}x.register.disabled=true;x.result.textContent="Saving…";try{const r=await fetch("/melimi/register",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify({word:source,root:x.root.value.trim(),meaning:x.meaning.value.trim(),part_of_speech:x.pos.value.trim(),melimi_equivalent:melimi,formation:x.formation.value.trim()})});const d=await r.json();if(!r.ok)throw Error(d.detail||"Registration failed");x.result.style.color="#8ed9a0";x.result.textContent="Saved as a controlled learning candidate.";setTimeout(()=>{closeWordModal();loadConversations()},700)}catch(e){x.result.style.color="#ef7777";x.result.textContent=e.message||"Could not save."}finally{x.register.disabled=false}});

setMode("melimi");resizeInput();checkAuth();

/* New knowledge/content entry menu */
(function(){
  const menu=document.getElementById("addContentModal");
  const open=document.getElementById("addContentButton");
  const close=document.getElementById("closeAddContent");
  const backdrop=document.getElementById("addContentBackdrop");
  const contentOption=document.getElementById("addContentOption");
  const wordOption=document.getElementById("addWordOption");

  function show(){ if(!menu)return; menu.classList.remove("hidden"); menu.setAttribute("aria-hidden","false"); }
  function hide(){ if(!menu)return; menu.classList.add("hidden"); menu.setAttribute("aria-hidden","true"); }
  open?.addEventListener("click",show);
  close?.addEventListener("click",hide);
  backdrop?.addEventListener("click",hide);
  document.addEventListener("keydown",e=>{if(e.key==="Escape" && menu && !menu.classList.contains("hidden"))hide()});

  contentOption?.addEventListener("click",()=>{
    hide();
    openKnowledgeContentModal();
  });
  wordOption?.addEventListener("click",()=>{
    hide();
    openWordModal();
  });
})();
