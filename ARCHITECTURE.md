# Transfer Booth Architecture & Technical Documentation

This document provides a detailed technical breakdown of the underlying protocols, architectural decisions, and security models that power Transfer Booth.

## 1. System Overview

Transfer Booth is fundamentally a two-tiered Local Area Network (LAN) application:
1.  **Discovery Layer (UDP):** A connectionless broadcast protocol responsible for finding peers, advertising availability, and managing ephemeral identities.
2.  **Transfer Layer (TCP):** A stateful, encrypted, point-to-point binary protocol responsible for high-throughput file transmission.

The application is bundled into a single executable using `PyInstaller`. When launched, a Python `FastAPI` instance starts a background daemon managing the UDP/TCP sockets, while a `pywebview` chromium-based window spawns to render the compiled React Single Page Application (SPA).

---

## 2. Network Discovery Protocol (UDP)

The Discovery service (`backend/discovery/service.py`) operates on UDP port `41234`. It continuously broadcasts and listens for `DiscoveryBeacon` JSON payloads every 3 seconds.

### 2.1 Interface Binding (`psutil`)
To prevent discovery beacons from leaking into Virtual Private Networks (VPNs) like Tailscale, or Hypervisor bridges like Docker/VirtualBox, the application uses `psutil.net_if_addrs()` to map exact OS-level hardware network adapters. A strict Denylist (filtering names like `tailscale0`, `wg`, `veth`) is applied before firing beacons using the exact subnet broadcast IPs derived from the physical local interfaces.

### 2.2 Ephemeral Identity Obfuscation
Transfer Booth enforces privacy by masking a user's real `DEVICE_NAME` (e.g., `DESKTOP-8GH2B`).
-   Upon startup, the `IdentityService` generates a random ephemeral X25519 keypair and an anonymous alias (e.g., `Neon Fox`).
-   The UDP `DiscoveryBeacon` advertises this ephemeral public key and alias.
-   Users on the LAN only see "Neon Fox" in their Device List.

### 2.3 Cryptographic TrustStore
When two peers successfully complete a file transfer, they exchange signed payloads containing their "Real" `DEVICE_NAME`s.
-   These real names and public keys are saved to a local `.transferbooth/trust_store.json`.
-   During future UDP discoveries, if an incoming beacon is signed by a recognized public key from the `TrustStore`, the UI replaces the ephemeral alias with the trusted Real Name (e.g., "Dave").

---

## 3. Transfer Protocol (TCP)

File transfers operate over raw, chunked TCP sockets dynamically assigned between ports `50000` and `65000`. The protocol handles backpressure, pausing, resumption, and cryptographic framing explicitly (`backend/transfer/service.py`).

### 3.1 Handshake & Key Exchange (E2EE)
When the Sender connects to the Receiver's TCP port:
1.  Both peers generate fresh, one-time `X25519` keypairs.
2.  They exchange public keys over the socket.
3.  Both sides derive a shared secret.
4.  `HKDF-SHA256` is used to stretch the shared secret into a 32-byte session key.
5.  All subsequent TCP traffic is authenticated and encrypted using `AES-256-GCM`.

### 3.2 Producer / Consumer Pipelining
To achieve Gigabit throughput (>100MB/s), the blocking bottlenecks of Disk I/O, Cryptography, and Network I/O were decoupled using `asyncio.Queue` bounded buffers.

*   **Sender Pipeline:** An `asyncio.Task` (Producer) continuously reads bytes from the SSD, dispatches them to a thread-pool for `AES-GCM` encryption, and places them in an `asyncio.Queue`. The main loop (Consumer) pulls from the queue and flushes directly to the TCP Buffer.
*   **Receiver Pipeline:** An `asyncio.Task` reads encrypted chunks from the TCP stream and places them into the queue. The Consumer pops the chunks, dispatches them to a thread-pool for decryption, and writes to the SSD.

This strictly parallelizes network transmission with CPU-bound cryptographic operations.

### 3.3 Payload Overhead & Framing
Files are chunked prior to encryption. The chunk size (defined in `config.py`) is set to `4MB`.
*   A 1GB transfer strictly requires only ~250 `asyncio.to_thread` context switches, heavily minimizing Python Global Interpreter Lock (GIL) thrashing.
*   Each `4MB` chunk is encapsulated in a generic message framing consisting of: `[Message Type (1 byte)] [Payload Length (4 bytes)] [AES-GCM Payload (Nonce + Ciphertext + Tag)]`.

---

## 4. Security Mitigations & Threat Modeling

Transfer Booth implements aggressive countermeasures against common P2P vulnerabilities:

*   **Memory Exhaustion (OOM) DoS:** The `asyncio.Queue` pipelines are strictly bounded (`maxsize=4`). If a rogue peer attempts to flood an unbounded TCP stream with gigabytes of data faster than the SSD can write, the queue blocks the socket ingestion, preventing the application RAM footprint from exploding.
*   **Cryptography Amplification Attacks:** Because chunks are 4MB, a malicious peer could send gigabytes of malformed AES-GCM payloads, forcing the victim's CPU to thrash attempting to authenticate invalid authentication tags. The `receive_file` stream implements a strict "3-Strikes" exception handler paired with an `asyncio.wait_for` timeout. If 3 decryption failures are registered, it assumes a Malformed Chunk Attack and aggressively tears down the TCP socket.

---

## 5. Local Database Capabilities
All inbound and outbound transfers are persisted via Python's built-in `sqlite3` driver (`backend/transfer/history.py`), stored in `~/.transferbooth/history.db`.

This schema provides a permanent `Transfers` table recording:
-   `transfer_id` (UUID)
-   `file_name` & `file_size`
-   `peer_device_name`
-   `direction` (SEND/RECEIVE)
-   `status` (COMPLETED, CANCELLED, FAILED)
-   `timestamp`

The frontend queries this `/api/history` REST endpoint to populate the Global Transfer History tab.

---

## 6. Frontend Stack (React SPA)
The frontend (`frontend/src/`) communicates with the FastAPI backend through two distinct channels:
1.  **Axios (REST):** Used for stateless commands (e.g., `get_devices()`, `create_transfer()`, `get_history()`).
2.  **Socket.IO (WebSockets):** Driven by `engineio/python-socketio`, providing sub-millisecond, bi-directional pub/sub for real-time state updates (e.g., Progress Bar percentages, Mbps speed outputs, Discovery arrivals).

It leverages `framer-motion` for complex UI state transitions (like springing physics boundaries on the progress bar) and dynamically taps into `DataTransferItem.getAsFile()` injections provided by PyWebView to emulate native Windows drag-and-drop operations directly onto DOM elements.
