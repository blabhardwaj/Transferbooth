"""
TCP-based file transfer service.

Handles the wire protocol for sending and receiving files,
including ECDH handshake, encrypted chunked transfer, pause/resume/cancel,
and transfer resumption from offset.
"""

import asyncio
import json
import logging
import os
import struct
import time
import uuid
from pathlib import Path

from config import CHUNK_SIZE, DEVICE_ID, DEVICE_NAME, TRANSFER_PORT_MIN, TRANSFER_PORT_MAX
from security.crypto import (
    generate_keypair,
    derive_shared_key,
    encrypt_chunk,
    decrypt_chunk,
)
from transfer.models import (
    FileMetadata,
    MessageType,
    TransferDirection,
    TransferInfo,
    TransferState,
)

logger = logging.getLogger(__name__)

# --- Wire protocol helpers ---

HEADER_FORMAT = "!BI"  # 1-byte type + 4-byte length (big-endian)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


async def send_message(
    writer: asyncio.StreamWriter, msg_type: int, payload: bytes = b""
) -> None:
    """Send a type-length-payload message."""
    header = struct.pack(HEADER_FORMAT, msg_type, len(payload))
    writer.write(header + payload)
    await writer.drain()


async def recv_message(
    reader: asyncio.StreamReader,
) -> tuple[int, bytes]:
    """Receive a type-length-payload message. Returns (type, payload)."""
    header = await reader.readexactly(HEADER_SIZE)
    msg_type, length = struct.unpack(HEADER_FORMAT, header)
    payload = b""
    if length > 0:
        payload = await reader.readexactly(length)
    return msg_type, payload


async def perform_handshake_sender(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> bytes:
    """
    Perform ECDH handshake as the sender (initiator).
    Returns the derived AES session key.
    """
    private_key, pub_bytes = generate_keypair()

    # Send our public key
    await send_message(writer, MessageType.HANDSHAKE_PUBKEY, pub_bytes)

    # Receive peer's public key
    msg_type, peer_pub_bytes = await recv_message(reader)
    if msg_type != MessageType.HANDSHAKE_PUBKEY:
        raise ConnectionError(f"Expected HANDSHAKE_PUBKEY, got {msg_type:#x}")

    return derive_shared_key(private_key, peer_pub_bytes)


async def perform_handshake_receiver(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> bytes:
    """
    Perform ECDH handshake as the receiver.
    Returns the derived AES session key.
    """
    private_key, pub_bytes = generate_keypair()

    # Receive peer's public key
    msg_type, peer_pub_bytes = await recv_message(reader)
    if msg_type != MessageType.HANDSHAKE_PUBKEY:
        raise ConnectionError(f"Expected HANDSHAKE_PUBKEY, got {msg_type:#x}")

    # Send our public key
    await send_message(writer, MessageType.HANDSHAKE_PUBKEY, pub_bytes)

    return derive_shared_key(private_key, peer_pub_bytes)


class SpeedTracker:
    """Rolling average speed calculator."""

    def __init__(self, window: float = 2.0):
        self._window = window
        self._samples: list[tuple[float, int]] = []

    def record(self, byte_count: int) -> None:
        now = time.monotonic()
        self._samples.append((now, byte_count))
        # Trim old samples
        cutoff = now - self._window
        self._samples = [(t, b) for t, b in self._samples if t >= cutoff]

    def get_speed(self) -> float:
        """Returns speed in bytes/sec."""
        if len(self._samples) < 2:
            return 0.0
        total_bytes = sum(b for _, b in self._samples[1:])
        elapsed = self._samples[-1][0] - self._samples[0][0]
        if elapsed <= 0:
            return 0.0
        return total_bytes / elapsed


async def _monitor_remote_commands(
    reader: asyncio.StreamReader,
    transfer_info: TransferInfo,
    state_callback,
) -> None:
    """(Sender side) Listen for commands from receiver while sending."""
    try:
        while transfer_info.state not in (
            TransferState.COMPLETED,
            TransferState.FAILED,
            TransferState.CANCELLED,
        ):
            # We use a small timeout or just wait. recv_message awaits header.
            # Only READ messages here.
            try:
                msg_type, _ = await recv_message(reader)
            except asyncio.IncompleteReadError:
                break
            except Exception:
                break

            if msg_type == MessageType.PAUSE:
                logger.info(f"Received PAUSE from receiver for {transfer_info.file_name}")
                transfer_info.state = TransferState.PAUSED_BY_PEER
                await state_callback(transfer_info)
            elif msg_type == MessageType.RESUME:
                logger.info(f"Received RESUME from receiver for {transfer_info.file_name}")
                transfer_info.state = TransferState.TRANSFERRING
                await state_callback(transfer_info)
            elif msg_type == MessageType.CANCEL:
                logger.info(f"Received CANCEL from receiver for {transfer_info.file_name}")
                transfer_info.state = TransferState.CANCELLED
                await state_callback(transfer_info)
                return
    except asyncio.CancelledError:
        pass


async def _monitor_local_state(
    writer: asyncio.StreamWriter,
    transfer_info: TransferInfo,
) -> None:
    """(Receiver side) Watch for local state changes and send commands."""
    last_state = transfer_info.state
    try:
        while transfer_info.state not in (
            TransferState.COMPLETED,
            TransferState.FAILED,
            TransferState.CANCELLED,
            TransferState.REJECTED,
        ):
            # Check for state changes initiated by UI (TransferManager)
            current = transfer_info.state
            
            if current != last_state:
                if current == TransferState.PAUSED and last_state == TransferState.TRANSFERRING:
                    logger.info(f"Sending PAUSE to sender for {transfer_info.file_name}")
                    await send_message(writer, MessageType.PAUSE)
                elif current == TransferState.TRANSFERRING and last_state == TransferState.PAUSED:
                    logger.info(f"Sending RESUME to sender for {transfer_info.file_name}")
                    await send_message(writer, MessageType.RESUME)
                elif current == TransferState.CANCELLED:
                    logger.info(f"Sending CANCEL to sender for {transfer_info.file_name}")
                    await send_message(writer, MessageType.CANCEL)
                    return # Exit loop on cancel

                last_state = current
            
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Local state monitor error: {e}")


async def send_file(
    peer_ip: str,
    peer_port: int,
    file_path: str,
    transfer_info: TransferInfo,
    progress_callback,
    state_callback,
    identity_service = None,
    trust_store = None,
) -> None:
    """
    Send a single file to a peer.

    Args:
        peer_ip: IP address of the receiver.
        peer_port: TCP port the receiver is listening on.
        file_path: Local path of the file to send.
        transfer_info: TransferInfo object (mutated in-place for progress).
        progress_callback: async fn(transfer_info) called on progress.
        state_callback: async fn(transfer_info) called on state change.
    """
    reader: asyncio.StreamReader | None = None
    writer: asyncio.StreamWriter | None = None
    monitor_task: asyncio.Task | None = None

    try:
        transfer_info.state = TransferState.CONNECTING
        await state_callback(transfer_info)

        reader, writer = await asyncio.open_connection(peer_ip, peer_port)

        # 1. ECDH Handshake
        session_key = await perform_handshake_sender(reader, writer)

        # 2. Send metadata
        signature = ""
        pub_key = ""
        if identity_service:
            pub_key = identity_service.get_public_bytes().hex()
            signature = identity_service.sign(transfer_info.transfer_id.encode('utf-8')).hex()

        metadata = FileMetadata(
            transfer_id=transfer_info.transfer_id,
            file_name=transfer_info.file_name,
            file_size=transfer_info.file_size,
            sender_device_id=identity_service.public_id if identity_service else DEVICE_ID,
            sender_device_name=identity_service.alias if identity_service else DEVICE_NAME,
            identity_public_key=pub_key,
            identity_signature=signature,
        )
        metadata_json = json.dumps(metadata.model_dump()).encode("utf-8")
        await send_message(writer, MessageType.METADATA, metadata_json)

        # 3. Wait for accept/reject
        msg_type, payload = await recv_message(reader)
        if msg_type == MessageType.REJECT:
            transfer_info.state = TransferState.REJECTED
            await state_callback(transfer_info)
            return
        if msg_type != MessageType.ACCEPT:
            raise ConnectionError(f"Expected ACCEPT/REJECT, got {msg_type:#x}")

        peer_identity = None
        if payload and trust_store:
            try:
                data = json.loads(payload.decode('utf-8'))
                pk = data.get('identity_public_key')
                sig = data.get('identity_signature')
                real_name = data.get('device_name')
                
                from cryptography.hazmat.primitives.asymmetric import ed25519
                pub_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pk))
                pub_key_obj.verify(bytes.fromhex(sig), transfer_info.transfer_id.encode('utf-8'))
                peer_identity = (transfer_info.peer_device_id, real_name, pk)
                transfer_info.peer_device_name = real_name
                await state_callback(transfer_info)
            except Exception as e:
                logger.warning(f"Failed to verify receiver identity: {e}")

        # 4. Receive resume offset
        msg_type, offset_data = await recv_message(reader)
        if msg_type != MessageType.RESUME_OFFSET:
            raise ConnectionError(f"Expected RESUME_OFFSET, got {msg_type:#x}")
        offset = struct.unpack("!Q", offset_data)[0]

        # 5. Start sending chunks
        transfer_info.state = TransferState.TRANSFERRING
        transfer_info.transferred_bytes = offset
        await state_callback(transfer_info)

        # START MONITORING FOR REMOTE COMMANDS (PAUSE/RESUME from receiver)
        monitor_task = asyncio.create_task(
            _monitor_remote_commands(reader, transfer_info, state_callback)
        )

        tracker = SpeedTracker()
        last_progress_time = time.monotonic()

        with open(file_path, "rb") as f:
            f.seek(offset)
            while True:
                # Check for pause/cancel
                if transfer_info.state == TransferState.CANCELLED:
                    await send_message(writer, MessageType.CANCEL)
                    return
                if transfer_info.state in (TransferState.PAUSED, TransferState.PAUSED_BY_PEER):
                    if transfer_info.state == TransferState.PAUSED:
                        await send_message(writer, MessageType.PAUSE)
                    
                    while transfer_info.state in (TransferState.PAUSED, TransferState.PAUSED_BY_PEER):
                        await asyncio.sleep(0.1)
                    
                    if transfer_info.state == TransferState.CANCELLED:
                        await send_message(writer, MessageType.CANCEL)
                        return
                    
                    if transfer_info.state == TransferState.TRANSFERRING:
                        await send_message(writer, MessageType.RESUME)

                chunk = await asyncio.to_thread(f.read, CHUNK_SIZE)
                if not chunk:
                    break

                encrypted = await asyncio.to_thread(encrypt_chunk, session_key, chunk)
                await send_message(writer, MessageType.DATA_CHUNK, encrypted)

                transfer_info.transferred_bytes += len(chunk)
                tracker.record(len(chunk))

                # Update progress at most every 200ms
                now = time.monotonic()
                if now - last_progress_time >= 0.2:
                    transfer_info.speed_bps = tracker.get_speed()
                    transfer_info.progress_percent = (
                        transfer_info.transferred_bytes / transfer_info.file_size * 100
                        if transfer_info.file_size > 0
                        else 100
                    )
                    remaining_bytes = transfer_info.file_size - transfer_info.transferred_bytes
                    transfer_info.eta_seconds = (
                        remaining_bytes / transfer_info.speed_bps
                        if transfer_info.speed_bps > 0
                        else 0
                    )
                    await progress_callback(transfer_info)
                    last_progress_time = now

        # 6. Send completion
        await send_message(writer, MessageType.TRANSFER_COMPLETE)
        
        if peer_identity and trust_store:
            trust_store.add_trusted_peer(*peer_identity)
            
        transfer_info.state = TransferState.COMPLETED
        transfer_info.progress_percent = 100.0
        transfer_info.speed_bps = 0
        transfer_info.eta_seconds = 0
        await state_callback(transfer_info)

    except asyncio.CancelledError:
        transfer_info.state = TransferState.CANCELLED
        await state_callback(transfer_info)
    except Exception as e:
        logger.error(f"Send error for {transfer_info.file_name}: {e}")
        if transfer_info.state != TransferState.CANCELLED:
            transfer_info.state = TransferState.FAILED
            transfer_info.error_message = str(e)
            await state_callback(transfer_info)
    finally:
        if monitor_task:
            monitor_task.cancel()
        
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def receive_file(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    save_dir: str,
    accept_callback,
    progress_callback,
    state_callback,
    identity_service = None,
    trust_store = None,
) -> TransferInfo | None:
    """
    Handle an incoming file transfer connection.

    Args:
        reader, writer: The TCP connection streams.
        save_dir: Directory to save the received file.
        accept_callback: async fn(transfer_info) -> bool — prompts user.
        progress_callback: async fn(transfer_info) called on progress.
        state_callback: async fn(transfer_info) called on state change.

    Returns:
        The TransferInfo of the completed transfer, or None if rejected.
    """
    transfer_info: TransferInfo | None = None
    monitor_task: asyncio.Task | None = None

    try:
        # 1. ECDH Handshake
        session_key = await perform_handshake_receiver(reader, writer)

        # 2. Receive metadata
        msg_type, metadata_raw = await recv_message(reader)
        if msg_type != MessageType.METADATA:
            raise ConnectionError(f"Expected METADATA, got {msg_type:#x}")

        metadata = FileMetadata(**json.loads(metadata_raw.decode("utf-8")))

        peer_identity = None
        real_sender_name = metadata.sender_device_name
        
        if metadata.identity_public_key and metadata.identity_signature and trust_store:
            try:
                from cryptography.hazmat.primitives.asymmetric import ed25519
                pub_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(metadata.identity_public_key))
                pub_key_obj.verify(bytes.fromhex(metadata.identity_signature), metadata.transfer_id.encode('utf-8'))
                
                known_peer = trust_store.get_peer_by_key(metadata.identity_public_key)
                if known_peer:
                    real_sender_name = known_peer.real_name
                
                peer_identity = (metadata.sender_device_id, real_sender_name, metadata.identity_public_key)
            except Exception as e:
                logger.warning(f"Failed to verify sender identity: {e}")

        transfer_info = TransferInfo(
            transfer_id=metadata.transfer_id,
            file_name=metadata.file_name,
            file_size=metadata.file_size,
            direction=TransferDirection.RECEIVING,
            peer_device_id=metadata.sender_device_id,
            peer_device_name=real_sender_name,
            state=TransferState.AWAITING_ACCEPTANCE,
        )
        await state_callback(transfer_info)

        # 3. Ask user to accept/reject
        accepted = await accept_callback(transfer_info)
        if not accepted:
            await send_message(writer, MessageType.REJECT)
            transfer_info.state = TransferState.REJECTED
            await state_callback(transfer_info)
            return transfer_info

        accept_payload = {}
        if identity_service:
            accept_payload = {
                "identity_public_key": identity_service.get_public_bytes().hex(),
                "identity_signature": identity_service.sign(transfer_info.transfer_id.encode('utf-8')).hex(),
                "device_name": DEVICE_NAME,
            }
        await send_message(writer, MessageType.ACCEPT, json.dumps(accept_payload).encode('utf-8'))

        # 4. Check for partial file (resume support)
        file_path = os.path.join(save_dir, metadata.file_name)
        offset = 0
        if os.path.exists(file_path):
            offset = os.path.getsize(file_path)

        await send_message(
            writer, MessageType.RESUME_OFFSET, struct.pack("!Q", offset)
        )

        # 5. Start receiving chunks
        transfer_info.state = TransferState.TRANSFERRING
        transfer_info.transferred_bytes = offset
        await state_callback(transfer_info)

        # START MONITORING FOR LOCAL STATE CHANGES (Pause/Resume from UI)
        monitor_task = asyncio.create_task(
            _monitor_local_state(writer, transfer_info)
        )

        tracker = SpeedTracker()
        last_progress_time = time.monotonic()
        mode = "ab" if offset > 0 else "wb"

        with open(file_path, mode) as f:
            while True:
                if transfer_info.state == TransferState.CANCELLED:
                    return transfer_info

                msg_type, payload = await recv_message(reader)

                if msg_type == MessageType.TRANSFER_COMPLETE:
                    break
                elif msg_type == MessageType.CANCEL:
                    transfer_info.state = TransferState.CANCELLED
                    await state_callback(transfer_info)
                    return transfer_info
                elif msg_type == MessageType.PAUSE:
                    transfer_info.state = TransferState.PAUSED_BY_PEER
                    await state_callback(transfer_info)
                    continue
                elif msg_type == MessageType.RESUME:
                    transfer_info.state = TransferState.TRANSFERRING
                    await state_callback(transfer_info)
                    continue
                elif msg_type == MessageType.DATA_CHUNK:
                    decrypted = await asyncio.to_thread(decrypt_chunk, session_key, payload)
                    await asyncio.to_thread(f.write, decrypted)
                    await asyncio.to_thread(f.flush)

                    transfer_info.transferred_bytes += len(decrypted)
                    tracker.record(len(decrypted))

                    now = time.monotonic()
                    if now - last_progress_time >= 0.2:
                        transfer_info.speed_bps = tracker.get_speed()
                        transfer_info.progress_percent = (
                            transfer_info.transferred_bytes
                            / transfer_info.file_size
                            * 100
                            if transfer_info.file_size > 0
                            else 100
                        )
                        remaining = transfer_info.file_size - transfer_info.transferred_bytes
                        transfer_info.eta_seconds = (
                            remaining / transfer_info.speed_bps
                            if transfer_info.speed_bps > 0
                            else 0
                        )
                        await progress_callback(transfer_info)
                        last_progress_time = now
                else:
                    logger.warning(f"Unexpected message type during receive: {msg_type:#x}")

        # 6. Complete
        if peer_identity and trust_store:
            trust_store.add_trusted_peer(*peer_identity)
            
        transfer_info.state = TransferState.COMPLETED
        transfer_info.progress_percent = 100.0
        transfer_info.speed_bps = 0
        transfer_info.eta_seconds = 0
        await state_callback(transfer_info)
        return transfer_info

    except asyncio.CancelledError:
        if transfer_info:
            transfer_info.state = TransferState.CANCELLED
            await state_callback(transfer_info)
    except Exception as e:
        logger.error(f"Receive error: {e}")
        if transfer_info and transfer_info.state != TransferState.CANCELLED:
            transfer_info.state = TransferState.FAILED
            transfer_info.error_message = str(e)
            await state_callback(transfer_info)
    finally:
        if monitor_task:
            monitor_task.cancel()
        
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    return transfer_info
