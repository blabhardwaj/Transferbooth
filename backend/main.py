"""
Transfer Booth — FastAPI application entry point.

Starts the Discovery Service and Transfer Manager on startup,
serves the REST API and WebSocket endpoint.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.routes import init_routes, router
from api.websocket import ConnectionManager
from config import API_HOST, API_PORT, DEVICE_NAME
from discovery.service import DiscoveryService
from transfer.manager import TransferManager

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# --- Service singletons ---
discovery_service = DiscoveryService()
transfer_manager = TransferManager()
ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop background services."""
    logger.info("Starting Transfer Booth services...")

    # Wire up event broadcasting
    transfer_manager.on_event(ws_manager.handle_event)

    # Wire up peer discovery events
    async def on_peer_event(event: str, peer):
        await ws_manager.broadcast(event, peer.model_dump())

    discovery_service.on_peer_change(on_peer_event)

    # Start services
    await discovery_service.start()
    await transfer_manager.start(device_name=DEVICE_NAME)

    logger.info(
        f"Transfer Booth ready — "
        f"API: {API_HOST}:{API_PORT}, "
        f"Receiver port: {transfer_manager.receiver_port}"
    )

    yield

    # Shutdown
    logger.info("Shutting down Transfer Booth services...")
    await transfer_manager.stop()
    await discovery_service.stop()


# --- FastAPI app ---
app = FastAPI(
    title="Transfer Booth",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inject services into routes
init_routes(discovery_service, transfer_manager)
app.include_router(router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive; we don't expect client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info",
    )
