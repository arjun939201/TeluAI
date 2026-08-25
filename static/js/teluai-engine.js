(()=>{const $=s=>document.querySelector(s);const pill=$('#engineStatus');if(!pill)return;const set=(state,label,details='')=>{pill.className=`engine-pill ${state}`;pill.querySelector('.engine-dot').setAttribute('aria-label',label);pill.querySelector('.engine-label').textContent=label;pill.querySelector('.engine-details').textContent=details};const check=async()=>{try{const r=await fetch('/health',{credentials:'same-origin',cache:'no-store'});const d=await r.json();if(!r.ok)throw Error();set('ready','TeluAI Engine','Online · '+(d.vocabulary_entries??0)+' language entries')}catch{set('error','Engine unavailable','Check the server')}};check();setInterval(check,30000);

// Compatibility bridge: the current backend exposes /chat as JSON while the
// existing UI still consumes an SSE /chat/stream contract. Translate the JSON
// response into the small SSE envelope expected by professional.js.
const nativeFetch=window.fetch.bind(window);
window.fetch=async(input,init={})=>{
  const url=typeof input==='string'?input:input?.url||'';

  if(url==='/me/settings'){
    let requestInit=init;
    try{
      if(init?.method==='PUT'&&typeof init.body==='string'){
        const payload=JSON.parse(init.body||'{}');
        if(payload.preferred_mode!=='standard'){
          requestInit={...init,body:JSON.stringify({...payload,preferred_mode:'melimi'})};
        }
      }
    }catch(_){}
    const response=await nativeFetch(input,requestInit);
    if(init?.method==='PUT'||!response.ok)return response;
    try{
      const data=await response.clone().json();
      if(data.preferred_mode!=='standard')data.preferred_mode='melimi';
      return new Response(JSON.stringify(data),{status:response.status,statusText:response.statusText,headers:{'Content-Type':'application/json'}});
    }catch(_){return response}
  }

  if(url==='/chat/stream' && init?.method==='POST'){
    let requestInit=init;
    try{
      const payload=JSON.parse(init.body||'{}');
      // Melimi is the native product language. Standard Telugu is the only
      // explicit opt-out; legacy/auto clients are normalized here too.
      if(payload.mode!=='standard'){
        requestInit={...init,body:JSON.stringify({...payload,mode:'melimi'})};
      }
    }catch(_){}
    const response=await nativeFetch('/chat',requestInit);
    if(!response.ok)return response;
    let data;
    try{data=await response.clone().json()}catch{return response}
    const encoder=new TextEncoder();
    const stream=new ReadableStream({start(controller){
      const send=event=>controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
      send({type:'start',conversation_id:data.conversation_id});
      if(data.reply)send({type:'delta',text:data.reply});
      send({type:'done',message_id:data.message_id,conversation_id:data.conversation_id});
      controller.close();
    }});
    return new Response(stream,{status:response.status,statusText:response.statusText,headers:{'Content-Type':'text/event-stream','Cache-Control':'no-cache'}});
  }
  return nativeFetch(input,init);
};
})();