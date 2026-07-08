"""FastAPI app factory."""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from clasifica.config import settings
from clasifica.core.logging import setup_logging

setup_logging()


def create_app() -> FastAPI:
    app = FastAPI(title="ClasificaDocMuni API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from clasifica.api.routes import auth, config, documents, exports, migration, reports, search

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    # search debe registrarse ANTES que documents: el router de documents
    # define /documents/{documento_id} (conversión a UUID), que de lo contrario
    # capturaría /documents/search ("search" no es UUID → 422).
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(migration.router, prefix=api_prefix)
    app.include_router(exports.router, prefix=api_prefix)
    app.include_router(config.router, prefix=api_prefix)
    app.include_router(reports.router, prefix=api_prefix)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.websocket("/ws/documents/{documento_id}")
    async def ws_documento(websocket: WebSocket, documento_id: str) -> None:
        import redis.asyncio as aioredis

        await websocket.accept()
        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"document:{documento_id}:events")
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    data = msg["data"]
                    await websocket.send_text(data.decode() if isinstance(data, bytes) else json.dumps(data))
                await asyncio.sleep(0.05)
        except WebSocketDisconnect:
            pass
        finally:
            await pubsub.unsubscribe()
            await r.aclose()

    return app


app = create_app()
