from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from .router import v1_router


def application_factory() -> FastAPI:
    """
    Factory function to create a FastAPI application instance.

    Returns:
        FastAPI: An instance of the FastAPI application.
    """
    app = FastAPI(
        title="luxtj backend",
        description="stateless backend process for luxtj",
        version="0.0.1alpha",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)

    return app
