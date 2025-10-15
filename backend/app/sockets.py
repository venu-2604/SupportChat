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
        response = await handle_incoming_message(data)
        print(f"🔍 SOCKET: Emitting bot_message with related field: {response.get('related', [])}")
        print(f"🔍 SOCKET: Full response: {response}")
        await sio.emit("bot_message", response, to=sid)


