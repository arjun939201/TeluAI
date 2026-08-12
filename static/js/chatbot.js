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

function escapeHtml(v){
    return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
}
function renderMelimiText(text,audit){
    const map=new Map((audit||[]).map(x=>[x.word,x]));
    return String(text).split(/([\u0C00-\u0C7F]+|[A-Za-z]+(?:['’-][A-Za-z]+)*)/g).map(part=>{
        const x=map.get(part);
        if(!x) return escapeHtml(part);
        const cls=x.clickable ? "word-token unregistered" : "word-token";
        const title=x.loan ? "Loan/foreign word — click to teach Melimi" :
                    (x.melimi_gap ? "Melimi equivalent needed — click to teach" : "Melimi word");
        return `<span class="${cls}" data-word="${escapeHtml(part)}" title="${title}">${escapeHtml(part)}</span>`;
    }).join("");
}
function addMessage(text,role,melimi=false,audit=[]){
    const wrapper=document.createElement("div");
    wrapper.className=`message ${role}`;
    if(role==="assistant"&&melimi) wrapper.classList.add("melimi");
    const content=document.createElement("div");
    content.className="message-content";
    if(role==="assistant"&&melimi) content.innerHTML=renderMelimiText(text,audit);
    else content.textContent=text;
    wrapper.appendChild(content);
    chatContainer.appendChild(wrapper);
    scrollToBottom();
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


/* v9: delegated click handler. This works for newly-created chat messages too. */
document.addEventListener("click", function(event){
    const token=event.target.closest(".word-token.unregistered");
    if(token){
        event.preventDefault();
        event.stopPropagation();
        openWordModal(token.dataset.word || token.textContent.trim());
    }
});

function getWordModal(){
    return {
        modal:document.getElementById("wordModal"),
        title:document.getElementById("wordModalTitle"),
        source:document.getElementById("wordSource"),
        status:document.getElementById("wordStatus"),
        root:document.getElementById("wordRoot"),
        meaning:document.getElementById("wordMeaning"),
        pos:document.getElementById("wordPos"),
        melimi:document.getElementById("wordMelimi"),
        formation:document.getElementById("wordFormation"),
        result:document.getElementById("wordResult"),
        register:document.getElementById("registerWord")
    };
}
function closeWordModal(){
    const x=getWordModal();
    if(x.modal) x.modal.classList.add("hidden");
}
async function checkWordStatus(word){
    const x=getWordModal();
    if(!word){
        x.status.textContent="Type any Telugu or loan word to register its Melimi Telugu equivalent.";
        x.status.style.color="#aaa";
        return;
    }
    x.status.textContent="Checking the Melimi language subject...";
    x.status.style.color="#f0b95b";
    try{
        const response=await fetch("/melimi/word/"+encodeURIComponent(word));
        const data=await response.json();
        if(data.registered){
            x.status.textContent="Already registered in the Melimi language subject.";
            x.status.style.color="#8ed9a0";
        }else if(data.loan){
            x.status.textContent="Loan/foreign word — teach its Melimi Telugu equivalent.";
            x.status.style.color="#f06a6a";
        }else{
            x.status.textContent="Melimi equivalent needed — teach the language subject.";
            x.status.style.color="#f0b95b";
        }
        if(data.melimi_equivalent && !x.melimi.value) x.melimi.value=data.melimi_equivalent;
    }catch(error){
        x.status.textContent="Teach its Melimi Telugu equivalent.";
    }
}
async function openWordModal(word){
    const x=getWordModal();
    if(!x.modal) return;
    word=(word||"").trim();
    x.title.textContent=word?"పదం నమోదు":"కొత్త పదం చేర్చు";
    x.source.value=word;
    x.root.value=word;
    x.meaning.value="";
    x.pos.value="";
    x.melimi.value="";
    x.formation.value="";
    x.result.textContent="";
    x.result.style.color="#8ed9a0";
    x.modal.classList.remove("hidden");
    await checkWordStatus(word);
    setTimeout(()=>{ (word?x.melimi:x.source)?.focus(); },50);
}
document.getElementById("closeWordModal")?.addEventListener("click",closeWordModal);
document.getElementById("cancelWord")?.addEventListener("click",closeWordModal);
document.getElementById("wordModalBackdrop")?.addEventListener("click",closeWordModal);
document.getElementById("addWordButton")?.addEventListener("click",()=>openWordModal(""));
document.addEventListener("keydown",event=>{
    if(event.key==="Escape") closeWordModal();
});
document.getElementById("wordSource")?.addEventListener("blur",()=>{
    const x=getWordModal();
    const w=x.source.value.trim();
    if(!x.root.value.trim()) x.root.value=w;
    checkWordStatus(w);
});
document.getElementById("registerWord")?.addEventListener("click",async()=>{
    const x=getWordModal();
    const payload={
        word:x.source.value.trim(),
        root:x.root.value.trim(),
        meaning:x.meaning.value.trim(),
        part_of_speech:x.pos.value.trim(),
        melimi_equivalent:x.melimi.value.trim(),
        formation:x.formation.value.trim()
    };
    if(!payload.word){
        x.result.style.color="#ef7777";
        x.result.textContent="Enter the Telugu/loan word first.";
        x.source.focus();
        return;
    }
    if(!payload.melimi_equivalent){
        x.result.style.color="#ef7777";
        x.result.textContent="Enter the Melimi Telugu word first.";
        x.melimi.focus();
        return;
    }
    x.register.disabled=true;
    x.result.style.color="#aaa";
    x.result.textContent="Registering...";
    try{
        const response=await fetch("/melimi/register",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify(payload)
        });
        const data=await response.json();
        if(!response.ok) throw new Error(data.detail || "Registration failed");
        x.result.style.color="#8ed9a0";
        x.result.textContent="Registered. It is now part of the local Melimi language subject.";
        setTimeout(closeWordModal,700);
    }catch(error){
        x.result.style.color="#ef7777";
        x.result.textContent=error.message || "Could not register the word.";
    }finally{
        x.register.disabled=false;
    }
});
