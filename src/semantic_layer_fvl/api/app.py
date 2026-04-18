from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from semantic_layer_fvl.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Semantic Layer FVL API",
        description="API REST para búsqueda semántica sobre el knowledge base de la Fundación Valle del Lili.",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")
    return app
