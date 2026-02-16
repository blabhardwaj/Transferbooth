"""REST API routes for Transfer Booth."""

import logging
import os

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from config import DEFAULT_SAVE_DIR, DEVICE_NAME

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# These will be injected by main.py at startup
_discovery_service = None
_transfer_manager = None


def init_routes(discovery_service, transfer_manager) -> None:
    """Inject service dependencies into the routes module."""
    global _discovery_service, _transfer_manager
    _discovery_service = discovery_service
    _transfer_manager = transfer_manager


# --- Device Discovery ---

@router.get("/devices")
async def list_devices():
    """Return list of discovered peers."""
    peers = await _discovery_service.get_peers()
    return {"devices": [p.model_dump() for p in peers]}


# --- Transfers ---

class TransferRequestBody(BaseModel):
    peer_id: str
    file_paths: list[str]


@router.get("/transfers")
async def list_transfers():
    """Return all transfers (active + completed)."""
    transfers = _transfer_manager.get_transfers()
    return {"transfers": [t.model_dump() for t in transfers]}



@router.post("/select-files")
async def select_files():
    """Open a native file picker dialog on the host machine."""
    import tkinter as tk
    from tkinter import filedialog

    # Tkinter requires a root window, but we don't want to show it
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes("-topmost", True)  # Bring dialog to front

    file_paths = filedialog.askopenfilenames(title="Select files to transfer")
    root.destroy()
    
    return {"files": list(file_paths)}


class CreateTransferBody(BaseModel):
    peer_id: str
    file_paths: list[str]


@router.post("/transfers")
async def create_transfer(body: CreateTransferBody):
    """Initiate a file transfer to the specified peer using absolute file paths.
    
    No file upload is required; the backend reads files directly from disk.
    """
    # Find the peer
    peers = await _discovery_service.get_peers()
    peer = next((p for p in peers if p.device_id == body.peer_id), None)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    # Verify files exist
    valid_paths = []
    for path in body.file_paths:
        if os.path.isfile(path):
            valid_paths.append(path)
        else:
            logger.warning(f"Skipping invalid file path: {path}")

    if not valid_paths:
        raise HTTPException(status_code=400, detail="No valid files selected")

    # Queue the transfer
    infos = await _transfer_manager.queue_send(
        peer_ip=peer.ip_address,
        peer_port=peer.transfer_port,
        peer_device_id=peer.device_id,
        peer_device_name=peer.device_name,
        file_paths=valid_paths,
    )

    return {
        "transfers": [i.model_dump() for i in infos],
        "message": f"Queued {len(infos)} file(s) for transfer",
    }

async def pause_transfer(transfer_id: str):
    await _transfer_manager.pause_transfer(transfer_id)
    return {"status": "paused"}


@router.post("/transfers/{transfer_id}/resume")
async def resume_transfer(transfer_id: str):
    await _transfer_manager.resume_transfer(transfer_id)
    return {"status": "resumed"}


@router.post("/transfers/{transfer_id}/cancel")
async def cancel_transfer(transfer_id: str):
    await _transfer_manager.cancel_transfer(transfer_id)
    return {"status": "cancelled"}


@router.post("/transfers/{transfer_id}/accept")
async def accept_transfer(transfer_id: str):
    await _transfer_manager.respond_to_request(transfer_id, accept=True)
    return {"status": "accepted"}


@router.post("/transfers/{transfer_id}/reject")
async def reject_transfer(transfer_id: str):
    await _transfer_manager.respond_to_request(transfer_id, accept=False)
    return {"status": "rejected"}


# --- Settings ---

class SettingsBody(BaseModel):
    device_name: str | None = None
    save_dir: str | None = None


@router.get("/settings")
async def get_settings():
    return {
        "device_name": _discovery_service.device_name,
        "save_dir": _transfer_manager.save_dir,
    }


@router.put("/settings")
async def update_settings(body: SettingsBody):
    if body.device_name is not None:
        _discovery_service.device_name = body.device_name
    if body.save_dir is not None:
        if not os.path.isdir(body.save_dir):
            try:
                os.makedirs(body.save_dir, exist_ok=True)
            except OSError as e:
                raise HTTPException(
                    status_code=400, detail=f"Invalid directory: {e}"
                )
        _transfer_manager.save_dir = body.save_dir
    return {"status": "updated"}
