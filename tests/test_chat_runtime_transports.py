import asyncio
import json
from starlette.requests import Request
from app.chat import middleware
class _Decision: mode="auto"; use_melimi=False; language="telugu"
class _Turn: message="hello"; conversation_id="conversation-1"; history=[]; decision=_Decision(); prompt="canonical prompt"; metadata={"intent":"conversation"}
class _User: id=7
class _Provider:
    async def complete(self,prompt,history,message):
        assert prompt=="canonical prompt"; assert message=="hello"
        return {"answer":"నమస్కారం","model":"test-model","input_tokens":3,"output_tokens":2,"latency_ms":5}
    async def stream(self,prompt,history,message):
        assert prompt=="canonical prompt"
        yield {"type":"delta","text":"నమస్కా"}; yield {"type":"delta","text":"రం"}; yield {"type":"done","model":"test-model","input_tokens":3,"output_tokens":2,"latency_ms":5}
def _request(body,path="/chat"):
    raw=json.dumps(body).encode(); sent=False
    async def receive():
        nonlocal sent
        if sent: return {"type":"http.disconnect"}
        sent=True; return {"type":"http.request","body":raw,"more_body":False}
    scope={"type":"http","method":"POST","path":path,"headers":[(b"content-type",b"application/json")],"query_string":b"","scheme":"http","server":("testserver",80),"client":("testclient",1234)}
    return Request(scope,receive)
async def _async_turn(): return _Turn()
def test_json_chat_runtime_uses_canonical_prepared_turn(monkeypatch):
    async def run():
        monkeypatch.setattr(middleware,"get_llm_provider",lambda:_Provider()); monkeypatch.setattr(middleware,"direct_lookup",lambda message:None); monkeypatch.setattr(middleware,"clean_response",lambda text:text); monkeypatch.setattr(middleware,"append_user_message",lambda *args,**kwargs:None); monkeypatch.setattr(middleware,"append_assistant_message",lambda *args,**kwargs:101); monkeypatch.setattr(middleware,"save_usage",lambda *args,**kwargs:None); monkeypatch.setattr(middleware,"_prepare",lambda data,user:_async_turn())
        response=await middleware.handle_json(_request({"message":"hello"}),_User()); payload=json.loads(response.body)
        assert response.status_code==200; assert payload["reply"]=="నమస్కారం"; assert payload["conversation_id"]=="conversation-1"; assert payload["message_id"]==101; assert payload["local"] is False
    asyncio.run(run())
def test_stream_chat_runtime_uses_canonical_prepared_turn(monkeypatch):
    async def run():
        monkeypatch.setattr(middleware,"get_llm_provider",lambda:_Provider()); monkeypatch.setattr(middleware,"direct_lookup",lambda message:None); monkeypatch.setattr(middleware,"clean_response",lambda text:text); monkeypatch.setattr(middleware,"append_user_message",lambda *args,**kwargs:None); monkeypatch.setattr(middleware,"append_assistant_message",lambda *args,**kwargs:202); monkeypatch.setattr(middleware,"save_usage",lambda *args,**kwargs:None); monkeypatch.setattr(middleware,"_prepare",lambda data,user:_async_turn())
        response=await middleware.handle_stream(_request({"message":"hello"}),_User()); chunks=[chunk async for chunk in response.body_iterator]; events=[json.loads(chunk.removeprefix("data: ").strip()) for chunk in chunks]
        assert events[0]["type"]=="start"; assert [e["text"] for e in events if e["type"]=="delta"]==["నమస్కా","రం"]; assert events[-1]["type"]=="done"; assert events[-1]["message_id"]==202
    asyncio.run(run())
def test_message_edit_is_persistence_only(monkeypatch):
    async def run():
        calls=[]; monkeypatch.setattr(middleware,"edit_user_message",lambda *args:calls.append(args) or "conversation-1"); response=await middleware.handle_edit(_request({"content":"edited"},path="/messages/42"),_User(),42)
        assert response.status_code==200; assert json.loads(response.body)=={"ok":True,"conversation_id":"conversation-1","message_id":42,"content":"edited"}; assert calls==[(7,42,"edited")]
    asyncio.run(run())
