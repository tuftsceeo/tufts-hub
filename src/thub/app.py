"""
FastAPI application for Tufts Hub.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from thub.logging import (
    LoggingMiddleware,
    configure_logging,
    log_shutdown,
    log_startup,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan for startup and shutdown logging.
    """
    configure_logging()
    log_startup()
    yield
    log_shutdown()


app = FastAPI(title="Tufts Hub", lifespan=lifespan)
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def root():
    """
    Root endpoint placeholder.
    """
    return {"message": "Tufts Hub is running"}
