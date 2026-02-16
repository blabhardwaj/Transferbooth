
import subprocess
import sys
import shutil
from pathlib import Path

def build():
    # Paths
    backend_dir = Path(__file__).parent
    frontend_dist = backend_dir.parent / "frontend" / "dist"
    
    if not frontend_dist.exists():
        print(f"Error: Frontend dist not found at {frontend_dist}")
        sys.exit(1)

    print("--- Building Transfer Booth ---")
    
    # PyInstaller arguments
    args = [
        "pyinstaller",
        "main.py",
        "--name=TransferBooth",
        "--onefile",
        "--noconsole",  # Hide terminal window
        "--clean",
        "--noconfirm",
        # Include frontend assets. source;dest
        f"--add-data={frontend_dist};frontend/dist",
        
        # Hidden imports often missed by PyInstaller
        "--hidden-import=uvicorn",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=fastapi",
        "--hidden-import=starlette",
        "--hidden-import=engineio.async_drivers.aiohttp",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=webview",
        "--hidden-import=clr",  # pythonnet for pywebview on Windows
        "--hidden-import=System",
    ]
    
    # Run PyInstaller
    print(f"Running: {' '.join(str(a) for a in args)}")
    result = subprocess.run(args, cwd=backend_dir)
    
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(result.returncode)
        
    print("--- Build Success ---")
    dist_dir = backend_dir / "dist"
    exe_path = dist_dir / "TransferBooth.exe"
    print(f"Executable created at: {exe_path}")

if __name__ == "__main__":
    build()
