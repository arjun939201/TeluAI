"""Production ASGI entrypoint for TeluAI.

The original Main Chat frontend uses the streaming chat override. Keep that
middleware installed explicitly at the application boundary so the deployment
cannot accidentally start the FastAPI app without the streaming route.
"""
from app.main import app
from app.chat.middleware import ChatOverrideMiddleware

# Install the chat override before serving requests. This preserves the
# existing /chat, /chat/stream, regenerate and message-edit behavior used by
# the original frontend.
app.add_middleware(ChatOverrideMiddleware)

# Activate the separate Melimi Telugu Lab workspace. It wraps the chat layer
# so Lab requests receive Melimi context and Lab conversations remain isolated
# from Main Chat conversations.
from app import lab_server  # noqa: E402,F401
