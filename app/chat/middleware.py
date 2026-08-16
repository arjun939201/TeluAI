from __future__ import annotations
import asyncio,json,time
from fastapi import Request
from fastapi.responses import JSONResponse,StreamingResponse
from app.auth import COOKIE_NAME
from app.chat.persistence import append_assistant_message,append_user_message,branch_from_message,context_for,edit_user_message,ensure_conversation
from app.chat.router import route_message
from app.chat.service import prepare_prompt
from app.config import settings
from app.database import save_usage,user_from_session
from app.melimi.firewall import deterministic_repair
from app.melimi.lexical import direct_lookup
from app.response import clean_response
from app.groq_client import call_groq_detailed,stream_groq
from app.security import RATE_LIMITER,client_identifier,session_fingerprint

def _sse(payload):return 'data: '+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n\n'
def _friendly(exc):
    text=str(exc).lower()
    if 'rate' in text or '429' in text:return 'Too many requests right now. Please try again in a moment.'
    if 'authentication' in text or 'configured' in text:return 'AI service authentication is temporarily unavailable.'
    if 'timed out' in text:return 'The AI service took too long to respond. Please try again.'
    if 'connect' in text:return 'The AI service is temporarily unreachable. Please try again shortly.'
    return "I couldn't complete that response. Please try again."

def _allow(request):
    identity=f"{client_identifier(request)}:{session_fingerprint(request)}"
    return RATE_LIMITER.check(f'/chat:{identity}',30,60)
async def _prepare(data,user):
    message=str(data.get('message','')).strip()
    if not message:raise ValueError('Message cannot be empty.')
    requested_mode=str(data.get('mode','auto'))
    if requested_mode not in {'auto','standard','melimi'}:requested_mode='auto'
    cid=ensure_conversation(user.id,data.get('conversation_id'),message,requested_mode)
    history,summary=context_for(user.id,cid)
    if summary:history=[{'role':'system','content':'Conversation summary: '+summary}]+history
    decision,prompt,meta=prepare_prompt(message,requested_mode,history,user.id,response_length=str(data.get('response_length','normal')))
    return message,cid,history,decision,prompt,meta
async def handle_json(request,user):
    try:
        data=await request.json();message,cid,history,decision,prompt,meta=await _prepare(data,user);direct=direct_lookup(message) if decision.use_melimi else None
        if direct is not None:
            append_user_message(user.id,cid,message);aid=append_assistant_message(user.id,cid,direct,model='melimi-lexical',latency_ms=0)
            return JSONResponse({'reply':direct,'mode':'melimi','intent':'melimi_lookup','language':decision.language,'conversation_id':cid,'message_id':aid,'local':True})
        result=await call_groq_detailed(prompt,history,message);reply=clean_response(result['answer'])
        if decision.mode=='melimi':reply=deterministic_repair(reply)
        if not reply:raise RuntimeError('Empty response')
        append_user_message(user.id,cid,message);aid=append_assistant_message(user.id,cid,reply,model=result.get('model'),input_tokens=result.get('input_tokens'),output_tokens=result.get('output_tokens'),latency_ms=result.get('latency_ms'));save_usage(user.id,result.get('model'),result.get('input_tokens'),result.get('output_tokens'),'ok')
        return JSONResponse({'reply':reply,'mode':decision.mode,'intent':meta.get('intent','conversation'),'language':decision.language,'conversation_id':cid,'message_id':aid,'local':False})
    except ValueError as exc:return JSONResponse({'detail':str(exc)},status_code=400)
    except Exception as exc:
        try:save_usage(user.id,settings.groq_model,None,None,'error')
        except Exception:pass
        return JSONResponse({'detail':_friendly(exc)},status_code=502)
async def handle_stream(request,user,data=None):
    if data is None:
        try:data=await request.json()
        except Exception:return StreamingResponse(iter([_sse({'type':'error','message':'Invalid request.'}),_sse({'type':'done'})]),media_type='text/event-stream',status_code=400)
    try:message,cid,history,decision,prompt,meta=await _prepare(data,user)
    except ValueError as exc:return StreamingResponse(iter([_sse({'type':'error','message':str(exc)}),_sse({'type':'done'})]),media_type='text/event-stream',status_code=400)
    direct=direct_lookup(message) if decision.use_melimi else None
    async def generate():
        started=time.perf_counter();append_user_message(user.id,cid,message)
        yield _sse({'type':'start','conversation_id':cid,'mode':decision.mode,'intent':meta.get('intent','conversation'),'language':decision.language})
        if direct is not None:
            aid=append_assistant_message(user.id,cid,direct,model='melimi-lexical',latency_ms=0);yield _sse({'type':'delta','text':direct});yield _sse({'type':'done','message_id':aid,'local':True,'latency_ms':int((time.perf_counter()-started)*1000)});return
        parts=[];model=None;input_tokens=output_tokens=latency_ms=None
        try:
            async for event in stream_groq(prompt,history,message):
                if await request.is_disconnected():return
                if event['type']=='delta':parts.append(event['text']);yield _sse({'type':'delta','text':event['text']})
                elif event['type']=='done':model=event.get('model');input_tokens=event.get('input_tokens');output_tokens=event.get('output_tokens');latency_ms=event.get('latency_ms')
            reply=clean_response(''.join(parts));reply=deterministic_repair(reply) if decision.mode=='melimi' else reply
            if not reply:raise RuntimeError('Empty response')
            aid=append_assistant_message(user.id,cid,reply,model=model,input_tokens=input_tokens,output_tokens=output_tokens,latency_ms=latency_ms);save_usage(user.id,model,input_tokens,output_tokens,'ok');yield _sse({'type':'done','message_id':aid,'model':model,'latency_ms':latency_ms or int((time.perf_counter()-started)*1000)})
        except asyncio.CancelledError:return
        except Exception as exc:
            try:save_usage(user.id,model or settings.groq_model,None,None,'error')
            except Exception:pass
            yield _sse({'type':'error','message':_friendly(exc)});yield _sse({'type':'done','cancelled':False})
    return StreamingResponse(generate(),media_type='text/event-stream',headers={'Cache-Control':'no-cache, no-transform','Connection':'keep-alive','X-Accel-Buffering':'no'})
async def handle_edit(request,user,message_id):
    try:
        data=await request.json();content=str(data.get('content','')).strip()
        if not content:raise ValueError('Message cannot be empty.')
        cid=edit_user_message(user.id,message_id,content);return JSONResponse({'ok':True,'conversation_id':cid,'message_id':message_id,'content':content})
    except ValueError as exc:return JSONResponse({'detail':str(exc)},status_code=404 if 'not found' in str(exc).lower() else 400)
class ChatOverrideMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope.get('type')!='http':await self.app(scope,receive,send);return
        path=scope.get('path','');method=scope.get('method','').upper();intercept=(path=='/chat' and method=='POST') or (path=='/chat/stream' and method=='POST') or (path.startswith('/chat/') and method=='POST') or (path.startswith('/messages/') and method=='PATCH')
        if not intercept:await self.app(scope,receive,send);return
        request=Request(scope,receive);allowed,retry=_allow(request)
        if not allowed:
            response=JSONResponse(status_code=429,content={'detail':'Too many requests. Please try again shortly.'},headers={'Retry-After':str(retry)});await response(scope,receive,send);return
        user=user_from_session(request.cookies.get(COOKIE_NAME))
        if user is None:
            response=JSONResponse({'detail':'Authentication required.'},status_code=401);await response(scope,receive,send);return
        if path=='/chat':response=await handle_json(request,user)
        elif path=='/chat/stream':response=await handle_stream(request,user)
        elif path.startswith('/messages/'):
            try:message_id=int(path.rsplit('/',1)[1]);response=await handle_edit(request,user,message_id)
            except ValueError:response=JSONResponse({'detail':'Invalid message id.'},status_code=400)
        else:
            try:
                data=await request.json();message_id=int(data.get('message_id'));cid,message=branch_from_message(user.id,message_id);data={'message':message,'mode':data.get('mode','auto'),'conversation_id':cid,'response_length':data.get('response_length','normal')};response=await handle_stream(request,user,data)
            except Exception as exc:response=StreamingResponse(iter([_sse({'type':'error','message':_friendly(exc)}),_sse({'type':'done'})]),media_type='text/event-stream',status_code=400)
        await response(scope,receive,send)
