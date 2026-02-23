<div align="center">
  <img src="backend/icon.ico" width="128" alt="TransferBooth Logo" />
  <h1>Transfer Booth V1</h1>
  <p>A lightning-fast, secure, and modern peer-to-peer Gigabit LAN file transfer application built with Python (AsyncIO) and React (TypeScript).</p>
</div>

---

## 🚀 Features

### 🛡️ Privacy & Security First
- **Zero-Configuration Discovery:** Automatically discovers peers on the local network using robust `psutil`-filtered UDP UDP beacons (prevents leaking discovery broadcasts into VPNs, Docker containers, or VMs).
- **Ephemeral Identities:** Your real device name is masked behind a rotating ephemeral alias (e.g., `Neon Fox`) until a successful transfer establishes cryptographic trust.
- **End-to-End Encryption:** Perfect forward secrecy using ephemeral X25519 (ECDH) key exchanges and AES-256-GCM authenticated encryption for every single file transfer session.
- **Authentication:** `Ed25519` cryptographic signatures verify trusted peers to prevent impersonation on the LAN.
- **Anti-DoS Architecture:** Strict decryption verification timeouts and chunking limits forcefully tear down connections from malicious actors attempting amplified malformed-payload attacks.

### ⚡ Gigabit Performance
- **Asynchronous Pipelining:** The core architecture uses unbounded `asyncio.Queue` Producer/Consumer pipelines. CPU Cryptography, Disk I/O, and Network Socket dispatches run entirely concurrently.
- **Tuned Payloads:** Dynamic 4MB payload framing slashes Python's GIL context-switching overhead, allowing Python to push encrypted files at near-native LAN wire speeds.

### ✨ Native UI/UX
- **Standalone:** Runs entirely in its own PyWebView native window—no browser required.
- **Drag-and-Drop:** Drag files straight from your Windows desktop and drop them specifically onto a recipient's Device Card to instantly initiate a transfer.
- **Dynamic Context:** Real-time ETA calculations, rolling-average speed tracking (Mbps), and live Framer-Motion spring animations for transfer states.
- **Global History:** All incoming and outgoing transfer records are logged locally via a built-in SQLite history database for easy auditing.

---

## 📦 Installation

### Direct Execution (Windows)
1. Navigate to the latest release or clone the repository.
2. Run the standalone packaged executable: `TransferBooth.exe`
3. The application will launch a native window interface.

### Build From Source
**Prerequisites:** Python 3.12+, Node.js 18+

1. **Clone the repository:**
   ```bash
   git clone https://github.com/blabhardwaj/Transferbooth.git
   cd Transferbooth
   ```

2. **Frontend Setup (Vite / React):**
   ```bash
   cd frontend
   npm install
   npm run build
   ```

3. **Backend Setup & Python Packaging:**
   ```bash
   cd ../backend
   pip install -r requirements.txt
   
   # Run the PyInstaller build script
   python build_exe.py
   ```
   > The final `TransferBooth.exe` will be generated inside the `backend/dist/` folder, cleanly injecting the React static files and custom icons.

---

## 💡 Usage

1. Open `TransferBooth.exe` on two separate computers connected to the same Local Area Network (Wi-Fi or Ethernet).
2. The devices will automatically discover each other's ephemeral animal aliases.
3. Drag and drop any file directly onto the recipient's Device Card.
4. The receiving device will prompt the user to **Accept** or **Reject** the incoming connection.
5. Upon acceptance, the application performs an ECDH handshake, derives a session key, and transmits the AES-GCM encrypted chunks seamlessly.
6. The interface will display a real-time progress bar, Mbps speed, and ETA.
7. Upon completion, the ephemeral alias will resolve to the device's Real Name (e.g., `Dave-PC`) as the peers establish cryptographic trust for future transfers.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.12, FastAPI, Asyncio, `cryptography`
- **Frontend:** React, TypeScript, Vite, Framer Motion, Lucide Icons
- **Window Toolkit:** `pywebview`
- **Packaging:** PyInstaller
- **Protocol:** Custom binary framing protocol over raw TCP sockets
- **Database:** SQLite (Transfer History)

## License
MIT
