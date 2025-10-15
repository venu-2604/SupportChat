from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from .routers import auth, faq, tickets
from .routers import admin
from .sockets import register_socketio
from .core.config import settings
from .startup import register_events


def create_app() -> FastAPI:
    app = FastAPI(title="Customer Support Chatbot", openapi_url=f"{settings.API_PREFIX}/openapi.json")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["auth"])
    app.include_router(faq.router, prefix=settings.API_PREFIX, tags=["faq"])
    app.include_router(tickets.router, prefix=settings.API_PREFIX, tags=["tickets"])
    app.include_router(admin.router, prefix=settings.API_PREFIX, tags=["admin"])

    # Socket.IO
    sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
    asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)
    register_socketio(sio)
    register_events(app)

    # Expose attributes for uvicorn target
    app.state.sio = sio
    app.state.asgi = asgi_app
    return app


app = create_app()

# Uvicorn entry expects an ASGI callable; serve the Socket.IO wrapper
asgi = app.state.asgi


