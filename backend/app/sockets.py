import socketio
from .services.chat import handle_incoming_message


def register_socketio(sio: socketio.AsyncServer):
    @sio.event
    async def connect(sid, environ):
        await sio.emit("connected", {"sid": sid}, to=sid)

    @sio.event
    async def disconnect(sid):
        # no-op; could log
        pass

    @sio.event
    async def chat_message(sid, data):
        # data: { session_id, content, user_email? }
        try:
            print(f"🔍 SOCKET: Received chat_message: {data}", flush=True)
            response = await handle_incoming_message(data)
            print(f"🔍 SOCKET: Emitting bot_message with related field: {response.get('related', [])}", flush=True)
            print(f"🔍 SOCKET: Full response: {response}", flush=True)
            # Broadcast to all connected clients to avoid edge-cases with sid changes during upgrades
            await sio.emit("bot_message", response)
        except Exception as e:
            # Never fail silently; emit a safe fallback and log the error
            try:
                print(f"❌ SOCKET ERROR handling chat_message: {e}", flush=True)
            except Exception:
                pass
            fallback = {
                "session_id": data.get("session_id"),
                "role": "assistant",
                "content": "Sorry, I hit an error processing that. Please try again in a moment.",
                "related": [],
            }
            await sio.emit("bot_message", fallback)


