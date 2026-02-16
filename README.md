# Transfer Booth V1

A fast, secure, and modern peer-to-peer file transfer application for LAN environments. Built with Python (FastAPI) and React (TypeScript).

## Features 🚀

- **Zero-Configuration:** Automatically discovers peers on the local network.
- **Secure:** End-to-end encryption using X25519 key exchange and AES-256-GCM.
- **Fast:** Direct peer-to-peer relationships using TCP.
- **Native Experience:** Runs in its own window (no browser required) with native file dialogs.
- **Robust:** Support for pausing, resuming, and recovering interrupted transfers.
- **Modern UI:** Responsive, animated interface built with React and Framer Motion.

## Installation 📦

### Standalone Executable (Windows)

1. Download the latest release `TransferBooth.exe`.
2. Run it! (No installation required).
3. The application will launch in a native window.

### From Source

**Prerequisites:** Python 3.10+, Node.js 18+

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/transferbooth.git
   cd transferbooth
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Usage 💡

1. Open the application on two devices connected to the same LAN.
2. The devices will automatically discover each other.
3. Click on a peer in the device list.
4. Select files using the native file picker.
5. Accept the transfer on the receiving device.
6. Watch the transfer progress!

## Technology Stack 🛠️

- **Backend:** Python, FastAPI, Asyncio, Cryptography
- **Frontend:** React, TypeScript, Vite, Framer Motion, Lucide
- **Protocol:** Custom TCP protocol with ECDH handshake and binary framing
- **Packaging:** PyInstaller

## License

MIT
