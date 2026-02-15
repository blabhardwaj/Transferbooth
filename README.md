# Transfer Booth

Fast, secure file transfer over your local network.

## Features

- 🔍 **Auto-Discovery** — Finds devices on your LAN automatically
- 🔒 **Encrypted** — AES-256-GCM with ephemeral ECDH keys
- ⏸️ **Pause / Resume / Cancel** — Full transfer control
- 📦 **Multi-File** — Send multiple files at once
- 📊 **Live Stats** — Speed, ETA, progress in real-time
- ✅ **Acceptance Prompt** — Receiver approves before transfer begins
- 🔄 **Resumable** — Interrupted transfers pick up where they left off

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, asyncio |
| Frontend | React 18, TypeScript, Vite |
| Networking | UDP broadcast (discovery), TCP (transfer) |
| Encryption | X25519 ECDH + AES-256-GCM |
| UI | Framer Motion, Lucide Icons |

## Quick Start

```bash
# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install

# Run backend (Terminal 1)
cd ../backend
python main.py

# Run frontend (Terminal 2)
cd ../frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## License

MIT
