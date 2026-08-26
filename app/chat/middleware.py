from __future__

import asyncio
import json
import time

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth import COOKIE_NAME
from app.chat.application import PreparedChatTurn, prepare_chat_turn
from app.chat.persistence import append_assistant_message, append_user_message, branch_from_message, edit_user_message
from app.chat_learning import learn_explicit_teaching, parse_command
from app.config import settings
from app.database import save_usage, user_from_session
from app.llm.provider import get_llm_provider
from app.melimi.firewall import deterministic_repair
from app.melimi.lexical import direct_lookup
from app.response import clean_response
from app.security import RATE_LIMITER, client_identifier, session_fingerprint
from app.groq_client import GroqProviderError, GroqRateLimitError
from app.learning.service import submit_command_candidate

def _sse(payload): return "data: " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n\n"
def _friendly(exc):
    if isinstance(exc, GroqRateLimitError): return str(exc)
    if isinstance(exc, GroqProviderError): return str(exc)
    text = str(exc).lower()
    if "rate" in text or "429" in text: return "Too many requests right now. Please try again in a moment."
    if "authentication" in text or "configured" in text: return "AI service authentication is temporarily unavailable."
    if "timed out" in text: return "The AI service took too long to respond. Please try again."
    if "connect" in text: return "The AI service is temporarily unreachable. Please try again shortly."
    return "I couldn't complete that response. Please try again."
def _error_payload(exc):
    payload = {"message": _friendly(exc), "retryable": getattr(exc, "retryable", False), "code": getattr(exc, "code", "chat_error")}
    retry = getattr(exc, "retry_after_seconds", None)
    if retry is not None: payload["retry_after_seconds"] = int(retry)
    return payload
def _allow(request): return RATE_LIMITER.check(f"/chat:{client_identifier(request)}:{session_fingerprint(request)}", 30, 60)
async def _prepare(data, user) -> PreparedChatTurn: return await prepare_chat_turn(data, user)
async def _language_command(message, user, cid):
    parsed = parse_command(message)
    if not parsed: raise ValueError("Invalid language command.")
    kind, payload = parsed
    if user.role in {"admin", "owner"}:
        result = learn_explicit_teaching(message, user.id)
        if not result.get("learned"): raise ValueError("Invalid language command.")
        status = "MASTER"; reply = "MASTER\n✓ మేలిమి భాషా నిలయంలో నేరుగా చేర్చబడింది.\nస్థితి: MASTER"
    else:
        submission = submit_command_candidate(kind, payload, message, user.id)
        status = "PENDING"; reply = "✓ మీ భాషా చేర్పు సమీక్షకు పంపబడింది.\nస్థితి: PENDING\nచేర్పు సంఖ్య: " + str(submission.candidate_id)
    append_user_message(user.id, cid, message); aid = append_assistant_message(user.id, cid, reply, model="language-command")
    return JSONResponse({"reply": reply, "mode": "melimi", "intent": "language_command", "language": "telugu", "conversation_id": cid, "message_id": aid, "local": True, "status": status})
async def handle_json(request, user):
    try:
        data = await request.json(); turn = await _prepare(data, user)
        if turn.message.startswith("/") and parse_command(turn.message): return await _language_command(turn.message, user, turn.conversation_id)
        direct = direct_lookup(turn.message) if turn.decision.use_melimi else None
        if direct is not None:
            append_user_message(user.id, turn.conversation_id, turn.message); aid = append_assistant_message(user.id, turn.conversation_id, direct, model="melimi-lexical", latency_ms=0)
            return JSONResponse({"reply": direct, "mode": "melimi", "intent": "melimi_lookup", "language": turn.decision.language, "conversation_id": turn.conversation_id, "message_id": aid, "local": True})
        result = await get_llm_provider().complete(turn.prompt, turn.history, turn.message); reply = clean_response(result["answer"]); reply = deterministic_repair(reply) if turn.decision.mode == "melimi" else reply
        if not reply: raise RuntimeError("Empty response")
        append_user_message(user.id, turn.conversation_id, turn.message); aid = append_assistant_message(user.id, turn.conversation_id, reply, model=result.get("model"), input_tokens=result.get("input_tokens"), output_tokens=result.get("output_tokens"), latency_ms=result.get("latency_ms")); save_usage(user.id, result.get("model"), result.get("input_tokens"), result.get("output_tokens"), "ok")
        return JSONResponse({"reply": reply, "mode": turn.decision.mode, "intent": turn.metadata.get("intent", "conversation"), "language": turn.decision.language, "conversation_id": turn.conversation_id, "message_id": aid, "local": False})
    except ValueError as exc: return JSONResponse({"detail": str(exc)}, status_code=400)
    except GroqRateLimitError as exc: return JSONResponse({"detail": _error_payload(exc)}, status_code=429, headers={"Retry-After": str(exc.retry_after_seconds)})
    except GroqProviderError as exc:
        try: save_usage(user.id, settings.groq_model, None, None, "error")
        except Exception: pass
        return JSONResponse({"detail": _error_payload(exc)}, status_code=503 if exc.retryable else 502)
    except Exception as exc:
        try: save_usage(user.id, settings.groq_model, None, None, "error")
        except Exception: pass
        return JSONResponse({"detail": _error_payload(exc)}, status_code=502)
async def handle_stream(request, user, data=None):
    if data is None:
        try: data = await request.json()
        except Exception: return StreamingResponse(iter([_sse({"type":"error","message":"Invalid request.","code":"invalid_request"}),_sse({"type":"done"})]), media_type="text/event-stream", status_code=400)
    try: turn = await _prepare(data, user)
    except ValueError as exc: return StreamingResponse(iter([_sse({"type":"error","message":str(exc),"code":"invalid_request"}),_sse({"type":"done"})]), media_type="text/event-stream", status_code=400)
    if turn.message.startswith("/") and parse_command(turn.message):
        response = await _language_command(turn.message, user, turn.conversation_id); payload = json.loads(response.body.decode("utf-8") if response.body else "{}")
        async def command_stream():
            yield _sse({"type":"start","conversation_id":turn.conversation_id,"mode":"melimi","intent":"language_command","language":"telugu"}); yield _sse({"type":"delta","text":payload.get("reply","")}); yield _sse({"type":"done","message_id":payload.get("message_id"),"local":True,"status":payload.get("status")})
        return StreamingResponse(command_stream(), media_type="text/event-stream", headers={"Cache-Control":"no-cache, no-transform"})
    direct = direct_lookup(turn.message) if turn.decision.use_melimi else None
    async def generate():
        started = time.perf_counter(); append_user_message(user.id, turn.conversation_id, turn.message); yield _sse({"type":"start","conversation_id":turn.conversation_id,"mode":turn.decision.mode,"intent":turn.metadata.get("intent","conversation"),"language":turn.decision.language})
        if direct is not None:
            aid = append_assistant_message(user.id, turn.conversation_id, direct, model="melimi-lexical", latency_ms=0); yield _sse({"type":"delta","text":direct}); yield _sse({"type":"done","message_id":aid,"local":True,"latency_ms":int((time.perf_counter()-started)*1000)}); return
        parts=[]; model=None; input_tokens=output_tokens=latency_ms=None
        try:
            async for event in get_llm_provider().stream(turn.prompt, turn.history, turn.message):
                if event["type"] == "delta": parts.append(event["text"]); yield _sse({"type":"delta","text":event["text"]})
                elif event["type"] == "done": model=event.get("model"); input_tokens=event.get("input_tokens"); output_tokens=event.get("output_tokens"); latency_ms=event.get("latency_ms")
            reply = clean_response("".join(parts)); reply = deterministic_repair(reply) if turn.decision.mode == "melimi" else reply
            if not reply: raise RuntimeError("Empty response")
            aid=append_assistant_message(user.id,turn.conversation_id,reply,model=model,input_tokens=input_tokens,output_tokens=output_tokens,latency_ms=latency_ms); save_usage(user.id,model,input_tokens,output_tokens,"ok"); yield _sse({"type":"done","message_id":aid,"model":model,"latency_ms":latency_ms or int((time.perf_counter()-started)*1000)})
        except asyncio.CancelledError: return
        except Exception as exc:
            try: save_usage(user.id,model or settings.groq_model,None,None,"error")
            except Exception: pass
            yield _sse({"type":"error",**_error_payload(exc)}); yield _sse({"type":"done","cancelled":False})
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control":"no-cache, no-transform","Connection":"keep-alive","X-Accel-Buffering":"no"})
async def handle_edit(request,user,message_id):
    try:
        data=await request.json(); content=str(data.get("content","")).strip()
        if not content: raise ValueError("Message cannot be empty.")
        cid=edit_user_message(user.id,message_id,content); return JSONResponse({"ok":True,"conversation_id":cid,"message_id":message_id,"content":content})
    except ValueError as exc: return JSONResponse({"detail":str(exc)},status_code=404 if "not found" in str(exc).lower() else 400)
class ChatOverrideMiddleware:
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope.get("type")!="http": await self.app(scope,receive,send); return
        path=scope.get("path",""); method=scope.get("method","").upper(); intercept=(path=="/chat" and method=="POST") or (path=="/chat/stream" and method=="POST") or (path.startswith("/chat/") and method=="POST") or (path.startswith("/messages/") and method=="PATCH")
        if not intercept: await self.app(scope,receive,send); return
        request=Request(scope,receive); allowed,retry=_allow(request)
        if not allowed:
            response=JSONResponse(status_code=429,content={"detail":{"message":"Too many requests. Please try again shortly.","code":"application_rate_limit","retryable":True,"retry_after_seconds":retry}},headers={"Retry-After":str(retry)}); await response(scope,receive,send); return
        user=user_from_session(request.cookies.get(COOKIE_NAME))
        if user is None: response=JSONResponse({"detail":"Authentication required."},status_code=401); await response(scope,receive,send); return
        if path=="/chat": response=await handle_json(request,user)
        elif path=="/chat/stream": response=await handle_stream(request,user)
        elif path.startswith("/messages/"):
            try: response=await handle_edit(request,user,int(path.rsplit("/",1)[1]))
            except ValueError: response=JSONResponse({"detail":"Invalid message id."},status_code=400)
        else:
            try:
                data=await request.json(); message_id=int(data.get("message_id")); cid,message=branch_from_message(user.id,message_id); data={"message":message,"mode":data.get("mode","auto"),"conversation_id":cid,"response_length":data.get("response_length","normal")}; response=await handle_stream(request,user,data)
            except Exception as exc: response=StreamingResponse(iter([_sse({"type":"error",**_error_payload(exc)}),_sse({"type":"done"})]),media_type="text/event-stream",status_code=400)
        await response(scope,receive,send)
