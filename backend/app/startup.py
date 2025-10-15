from fastapi import FastAPI
from .db.postgres import init_schema


def register_events(app: FastAPI) -> None:
    @app.on_event("startup")
    def on_startup():
        init_schema()


