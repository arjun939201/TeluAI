const chatContainer=document.getElementById("chatContainer");
const welcome=document.getElementById("welcome");
const chatForm=document.getElementById("chatForm");
const messageInput=document.getElementById("messageInput");
const sendButton=document.getElementById("sendButton");
const clearButton=document.getElementById("clearButton");
const mobileNewChat=document.getElementById("mobileNewChat");
const standardMode=document.getElementById("standardMode");
const melimiMode=document.getElementById("melimiMode");
const modelName=document.getElementById("modelName");

let mode="melimi",history=[],isSending=false;

function setMode(newMode){
    mode=newMode;
    standardMode.classList.toggle("active",mode==="standard");
    melimiMode.classList.toggle("active",mode==="melimi");
    modelName.textContent=mode==="melimi"?"మేలిమి తెలుగు AI":"తెలుగు AI";
    messageInput.placeholder=mode==="melimi"?"మేలిమి తెలుగులో అడుగు...":"తెలుగులో అడుగు...";
}
standardMode.addEventListener("click",()=>setMode("standard"));
melimiMode.addEventListener("click",()=>setMode("melimi"));

function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));}
function renderMelimiText(text,audit){
 const map=new Map((audit||[]).map(x=>[x.word,x]));
 return String(text).split(/([\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*)/g).map(part=>{
  const x=map.get(part); if(!x)return escapeHtml(part);
  return `<span class="word-token${x.clickable?" unregistered":""}" data-word="${escapeHtml(part)}">${escapeHtml(part)}</span>`;
 }).join("");
}
function addMessage(text,role,melimi=false,audit=[]){
 const wrapper=document.createElement("div");wrapper.className=`message ${role}`;
 if(role==="assistant"&&melimi)wrapper.classList.add("melimi");
 const content=document.createElement("div");content.className="message-content";
 if(role==="assistant"&&melimi){content.innerHTML=renderMelimiText(text,audit);
  content.querySelectorAll(".word-token").forEach(x=>x.onclick=()=>openWordModal(x.dataset.word));
 }else content.textContent=text;
 wrapper.appendChild(content);chatContainer.appendChild(wrapper);scrollToBottom();
}

function showTyping(){
    const wrapper=document.createElement("div");
    wrapper.id="typingIndicator";wrapper.className="typing-message";
    wrapper.innerHTML='<div class="typing"><span></span><span></span><span></span></div>';
    chatContainer.appendChild(wrapper);scrollToBottom();
}
function removeTyping(){document.getElementById("typingIndicator")?.remove()}
function addError(text){
    const wrapper=document.createElement("div");wrapper.className="error-message";
    const error=document.createElement("div");error.className="error";error.textContent=text;
    wrapper.appendChild(error);chatContainer.appendChild(wrapper);scrollToBottom();
}
function scrollToBottom(){requestAnimationFrame(()=>chatContainer.scrollTop=chatContainer.scrollHeight)}
function resizeInput(){messageInput.style.height="auto";messageInput.style.height=`${Math.min(messageInput.scrollHeight,160)}px`}
messageInput.addEventListener("input",resizeInput);

async function sendMessage(){
    if(isSending)return;
    const text=messageInput.value.trim();if(!text)return;
    isSending=true;sendButton.disabled=true;messageInput.value="";resizeInput();
    if(welcome)welcome.style.display="none";
    addMessage(text,"user");
    const previousHistory=[...history];
    showTyping();
    try{
        const response=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify({message:text,mode,history:previousHistory})});
        const data=await response.json().catch(()=>({}));
        removeTyping();
        if(!response.ok){addError(data.detail||`సర్వర్ లోపం: ${response.status}`);return}
        if(!data.reply){addError("AI నుండి సమాధానం రాలేదు.");return}
        addMessage(data.reply,"assistant",mode==="melimi",data.word_audit||[]);
        history.push({role:"user",content:text});
        history.push({role:"assistant",content:data.reply});
    }catch(error){
        removeTyping();console.error("TeluAI error:",error);
        addError("సర్వర్‌ను చేరుకోలేకపోయాము. మళ్లీ ప్రయత్నించు.");
    }finally{isSending=false;sendButton.disabled=false;messageInput.focus()}
}
chatForm.addEventListener("submit",e=>{e.preventDefault();sendMessage()});
messageInput.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage()}});
document.querySelectorAll(".suggestion").forEach(button=>button.addEventListener("click",()=>{
    const text=button.dataset.message;if(!text)return;messageInput.value=text;resizeInput();sendMessage();
}));
function newChat(){
    history=[];
    chatContainer.querySelectorAll(".message,.error-message,.typing-message").forEach(x=>x.remove());
    if(welcome)welcome.style.display="";
    messageInput.value="";resizeInput();messageInput.focus();
}
clearButton.addEventListener("click",newChat);
mobileNewChat.addEventListener("click",newChat);
setMode("melimi");resizeInput();messageInput.focus();

const wordModal=document.getElementById("wordModal"),backdrop=document.getElementById("wordModalBackdrop");
const selectedWord=document.getElementById("selectedWord"),wordStatus=document.getElementById("wordStatus");
const wordRoot=document.getElementById("wordRoot"),wordMeaning=document.getElementById("wordMeaning");
const wordPos=document.getElementById("wordPos"),wordMelimi=document.getElementById("wordMelimi");
const wordFormation=document.getElementById("wordFormation"),wordResult=document.getElementById("wordResult");
function closeWordModal(){wordModal.classList.add("hidden")}
document.getElementById("closeWordModal")?.addEventListener("click",closeWordModal);
document.getElementById("cancelWord")?.addEventListener("click",closeWordModal);
backdrop?.addEventListener("click",closeWordModal);
async function openWordModal(word){
 selectedWord.textContent=word;wordRoot.value=word;wordMeaning.value="";wordPos.value="";
 wordMelimi.value="";wordFormation.value="";wordResult.textContent="";
 wordStatus.textContent="Unregistered word — enter its Melimi equivalent.";
 wordModal.classList.remove("hidden");wordMelimi.focus();
}
document.getElementById("registerWord")?.addEventListener("click",async()=>{
 const payload={word:selectedWord.textContent,root:wordRoot.value,meaning:wordMeaning.value,
 part_of_speech:wordPos.value,melimi_equivalent:wordMelimi.value,formation:wordFormation.value};
 if(!payload.melimi_equivalent.trim()){wordResult.style.color="#ef9999";wordResult.textContent="Enter the Melimi word.";return}
 try{const r=await fetch("/melimi/register",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
 const d=await r.json();if(!r.ok)throw Error(d.detail||"Registration failed");
 wordResult.textContent="Registered in the Melimi language subject.";setTimeout(closeWordModal,700);
 }catch(e){wordResult.style.color="#ef9999";wordResult.textContent=e.message}
});
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeWordModal()});
