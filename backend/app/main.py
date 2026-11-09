"""Notes API: FastAPI + PostgreSQL, with a Redis cache on the list endpoint."""

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

import redis
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.cache import NOTES_KEY, Cache
from app.config import Settings, get_settings
from app.db import Base, Note, make_engine, make_sessionmaker
from app.schemas import NoteIn, NoteOut

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None, redis_client: Any | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_url)
        if settings.database_url.startswith("sqlite"):
            # Tests and local runs only. With PostgreSQL, tables are created once by
            # `python -m app.init_db` before the workers start (avoids a startup race).
            Base.metadata.create_all(engine)
        app.state.sessionmaker = make_sessionmaker(engine)
        client = redis_client or redis.Redis.from_url(
            settings.redis_url, decode_responses=True, socket_timeout=1, socket_connect_timeout=1
        )
        app.state.cache = Cache(client, settings.cache_ttl_seconds)
        yield
        engine.dispose()

    app = FastAPI(
        title="Notes API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    def get_db(request: Request):
        with request.app.state.sessionmaker() as session:
            yield session

    @app.get("/api/health")
    def health(request: Request) -> dict[str, str]:
        with request.app.state.sessionmaker() as session:
            session.execute(text("SELECT 1"))
        cache_state = "up" if request.app.state.cache.ping() else "down"
        return {"status": "ok", "database": "up", "cache": cache_state}

    @app.get("/api/notes", response_model=list[NoteOut])
    def list_notes(request: Request, db: Session = Depends(get_db)):
        cache: Cache = request.app.state.cache
        cached = cache.get(NOTES_KEY)
        if cached is not None:
            return Response(cached, media_type="application/json", headers={"X-Cache": "HIT"})

        rows = db.scalars(select(Note).order_by(Note.id.desc())).all()
        payload = json.dumps(jsonable_encoder([NoteOut.model_validate(r) for r in rows]))
        cache.set(NOTES_KEY, payload)
        return Response(payload, media_type="application/json", headers={"X-Cache": "MISS"})

    @app.post("/api/notes", response_model=NoteOut, status_code=201)
    def create_note(body: NoteIn, request: Request, db: Session = Depends(get_db)):
        note = Note(title=body.title.strip(), content=body.content.strip())
        db.add(note)
        db.commit()
        request.app.state.cache.invalidate(NOTES_KEY)
        return note

    @app.delete("/api/notes/{note_id}", status_code=204)
    def delete_note(note_id: int, request: Request, db: Session = Depends(get_db)):
        note = db.get(Note, note_id)
        if note is None:
            raise HTTPException(404, "Note not found")
        db.delete(note)
        db.commit()
        request.app.state.cache.invalidate(NOTES_KEY)

    return app
