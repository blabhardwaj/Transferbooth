"""
Transfer Manager — orchestrates multiple file transfers.

Manages a queue of transfers, tracks state, and coordinates
the Transfer Service with the WebSocket event system.
"""

import asyncio
import logging
import os
import random
import uuid

from config import (
    DEFAULT_SAVE_DIR,
    DEVICE_ID,
    TRANSFER_PORT_MIN,
    TRANSFER_PORT_MAX,
)
from transfer.models import (
    TransferDirection,
    TransferInfo,
    TransferState,
)
from transfer.service import receive_file, send_file

logger = logging.getLogger(__name__)


class TransferManager:
    """Manages all active and completed file transfers."""

    def __init__(self, identity_service, trust_store) -> None:
        self._transfers: dict[str, TransferInfo] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._event_callbacks: list = []  # async fn(event_type, data)
        self._accept_futures: dict[str, asyncio.Future] = {}
        self._receiver_server: asyncio.Server | None = None
        self._save_dir = DEFAULT_SAVE_DIR
        self._device_name = ""
        self._identity_service = identity_service
        self._trust_store = trust_store

    @property
    def save_dir(self) -> str:
        return self._save_dir

    @save_dir.setter
    def save_dir(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        self._save_dir = path

    def on_event(self, callback) -> None:
        """Register callback: async fn(event_type: str, data: dict)."""
        self._event_callbacks.append(callback)

    async def _emit(self, event_type: str, data: dict) -> None:
        """Emit an event to all registered callbacks."""
        for cb in self._event_callbacks:
            try:
                await cb(event_type, data)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    async def start(self, device_name: str) -> None:
        """Start the receiver listener on a random port."""
        self._device_name = device_name
        port = random.randint(TRANSFER_PORT_MIN, TRANSFER_PORT_MAX)

        # Try a few ports if the first one is busy
        for attempt in range(10):
            try:
                self._receiver_server = await asyncio.start_server(
                    self._handle_incoming_connection,
                    "0.0.0.0",
                    port,
                )
                logger.info(f"Transfer receiver listening on port {port}")
                self._receiver_port = port
                return
            except OSError:
                port = random.randint(TRANSFER_PORT_MIN, TRANSFER_PORT_MAX)

        raise RuntimeError("Could not bind to any transfer port")

    @property
    def receiver_port(self) -> int:
        return getattr(self, "_receiver_port", 0)

    async def stop(self) -> None:
        """Stop all transfers and the receiver listener."""
        # Cancel all active transfer tasks
        for tid, task in self._tasks.items():
            task.cancel()
        self._tasks.clear()

        if self._receiver_server:
            self._receiver_server.close()
            await self._receiver_server.wait_closed()

        logger.info("Transfer manager stopped")

    def get_transfers(self) -> list[TransferInfo]:
        """Return all transfers."""
        return list(self._transfers.values())

    async def queue_send(
        self, peer_ip: str, peer_port: int, peer_device_id: str,
        peer_device_name: str, file_paths: list[str]
    ) -> list[TransferInfo]:
        """Queue multiple files to send to a peer."""
        infos = []
        for file_path in file_paths:
            transfer_id = str(uuid.uuid4())
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            info = TransferInfo(
                transfer_id=transfer_id,
                file_name=file_name,
                file_size=file_size,
                direction=TransferDirection.SENDING,
                peer_device_id=peer_device_id,
                peer_device_name=peer_device_name,
                state=TransferState.PENDING,
            )

            async with self._lock:
                self._transfers[transfer_id] = info

            # Start a task for each file
            task = asyncio.create_task(
                self._send_file_task(peer_ip, peer_port, file_path, info)
            )
            self._tasks[transfer_id] = task
            infos.append(info)

            await self._emit("transfer_state", info.model_dump())

        return infos

    async def _send_file_task(
        self, peer_ip: str, peer_port: int, file_path: str, info: TransferInfo
    ) -> None:
        """Task wrapper for sending a single file."""
        await send_file(
            peer_ip=peer_ip,
            peer_port=peer_port,
            file_path=file_path,
            transfer_info=info,
            progress_callback=self._on_progress,
            state_callback=self._on_state_change,
            identity_service=self._identity_service,
            trust_store=self._trust_store,
        )
        # Clean up task reference
        self._tasks.pop(info.transfer_id, None)

    async def _handle_incoming_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a new incoming TCP connection for file reception."""
        await receive_file(
            reader=reader,
            writer=writer,
            save_dir=self._save_dir,
            accept_callback=self._prompt_accept,
            progress_callback=self._on_progress,
            state_callback=self._on_state_change,
            identity_service=self._identity_service,
            trust_store=self._trust_store,
        )

    async def _prompt_accept(self, transfer_info: TransferInfo) -> bool:
        """
        Prompt the user to accept/reject an incoming transfer.
        Creates a Future that will be resolved when the user decides.
        """
        async with self._lock:
            self._transfers[transfer_info.transfer_id] = transfer_info

        # Emit event so frontend can show the acceptance dialog
        await self._emit("transfer_request", transfer_info.model_dump())

        # Create a future that will be resolved by accept/reject API calls
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._accept_futures[transfer_info.transfer_id] = future

        try:
            # Wait up to 60 seconds for user response
            result = await asyncio.wait_for(future, timeout=60.0)
            return result
        except asyncio.TimeoutError:
            logger.info(f"Transfer {transfer_info.transfer_id} timed out waiting for acceptance")
            return False
        finally:
            self._accept_futures.pop(transfer_info.transfer_id, None)

    async def respond_to_request(self, transfer_id: str, accept: bool) -> None:
        """Resolve a pending acceptance prompt."""
        future = self._accept_futures.get(transfer_id)
        if future and not future.done():
            future.set_result(accept)

    async def pause_transfer(self, transfer_id: str) -> None:
        """Pause an active transfer."""
        info = self._transfers.get(transfer_id)
        if info and info.state == TransferState.TRANSFERRING:
            info.state = TransferState.PAUSED
            await self._on_state_change(info)

    async def resume_transfer(self, transfer_id: str) -> None:
        """Resume a paused transfer."""
        info = self._transfers.get(transfer_id)
        if info and info.state == TransferState.PAUSED:
            info.state = TransferState.TRANSFERRING
            await self._on_state_change(info)

    async def cancel_transfer(self, transfer_id: str) -> None:
        """Cancel a transfer."""
        info = self._transfers.get(transfer_id)
        if info and info.state in (
            TransferState.PENDING,
            TransferState.TRANSFERRING,
            TransferState.PAUSED,
            TransferState.PAUSED_BY_PEER,
            TransferState.AWAITING_ACCEPTANCE,
        ):
            info.state = TransferState.CANCELLED
            await self._on_state_change(info)

            # Cancel the asyncio task if it exists
            task = self._tasks.pop(transfer_id, None)
            if task:
                task.cancel()

    async def _on_progress(self, info: TransferInfo) -> None:
        """Called by transfer service on progress updates."""
        await self._emit("transfer_progress", info.model_dump())

    async def _on_state_change(self, info: TransferInfo) -> None:
        """Called by transfer service on state changes."""
        async with self._lock:
            self._transfers[info.transfer_id] = info
        await self._emit("transfer_state", info.model_dump())

        # Generate user-facing notifications
        notification = None
        if info.state == TransferState.COMPLETED:
            direction = "sent" if info.direction == TransferDirection.SENDING else "received"
            notification = {
                "type": "success",
                "message": f"'{info.file_name}' {direction} successfully!",
            }
        elif info.state == TransferState.FAILED:
            notification = {
                "type": "error",
                "message": f"Transfer of '{info.file_name}' failed: {info.error_message}",
            }
        elif info.state == TransferState.CANCELLED:
            notification = {
                "type": "info",
                "message": f"Transfer of '{info.file_name}' cancelled.",
            }
        elif info.state == TransferState.REJECTED:
            notification = {
                "type": "warning",
                "message": f"Transfer of '{info.file_name}' was rejected.",
            }

        if notification:
            await self._emit("notification", notification)
