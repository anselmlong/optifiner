"""Main FastAPI application."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from optifiner_api.api import router
from optifiner_api.config import settings
from optifiner_api.database import init_db, close_db
from optifiner_api.websocket import get_connection_manager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Closing database connections...")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title="Optifiner API",
    description="API for GitHub integration and worker agent coordination",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


# Include routers
app.include_router(router, prefix="/api/v1")


# WebSocket endpoints
@app.websocket("/ws/workflow/{workflow_id}")
async def websocket_workflow(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for workflow-specific updates."""
    manager = get_connection_manager()
    await manager.connect_workflow(websocket, workflow_id)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Client can send ping/pong or commands if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect_workflow(websocket, workflow_id)


@app.websocket("/ws/global")
async def websocket_global(websocket: WebSocket):
    """WebSocket endpoint for global updates (dashboard)."""
    manager = get_connection_manager()
    await manager.connect_global(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect_global(websocket)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Optifiner API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
