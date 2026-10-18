"""Cross-platform startup using only Python's standard library."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import venv

from model_settings import preferred_model

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / ".runtime"
MODEL = preferred_model(ROOT / "data")
URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def python_in(environment: Path, platform: str = sys.platform) -> Path:
    return environment / ("Scripts/python.exe" if platform == "win32" else "bin/python")


def setup_python() -> Path:
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required. Python 3.12 is recommended.")
    environment = ROOT / ".venv"
    executable = python_in(environment)
    if not executable.is_file():
        print("Creating the project Python environment…", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    requirements = ROOT / "requirements.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / ".receiptcheck-requirements"
    if not marker.is_file() or marker.read_text() != fingerprint:
        print("Installing app dependencies (first run only)…", flush=True)
        if subprocess.run([str(executable), "-m", "pip", "--version"], capture_output=True).returncode:
            subprocess.run([str(executable), "-m", "ensurepip", "--upgrade"], check=True)
        subprocess.run([str(executable), "-m", "pip", "install", "-r", str(requirements)], check=True)
        marker.write_text(fingerprint)
    return executable


def get_models():
    try:
        with urlopen(f"{URL}/api/tags", timeout=3) as response:
            return json.load(response).get("models", [])
    except (URLError, TimeoutError, OSError, ValueError):
        return None


def ensure_ollama():
    if get_models() is not None:
        return None
    executable = shutil.which("ollama")
    if not executable and sys.platform == "win32":
        installed = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if installed.is_file():
            executable = str(installed)
    if not executable:
        raise RuntimeError("Install Ollama from https://ollama.com/download, then run this launcher again.")
    if URL not in ("http://127.0.0.1:11434", "http://localhost:11434"):
        raise RuntimeError(f"The configured Ollama server at {URL} is unreachable. Start it and try again.")
    print("Starting local Ollama…", flush=True)
    RUNTIME.mkdir(exist_ok=True)
    with (RUNTIME / "ollama.log").open("ab") as log:
        process = subprocess.Popen([executable, "serve"], stdout=log, stderr=log,
                                   env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11434"})
    for _ in range(60):
        if get_models() is not None:
            return process
        if process.poll() is not None:
            break
        time.sleep(1)
    process.terminate() if process.poll() is None else None
    raise RuntimeError("Ollama could not start. Check .runtime/ollama.log and try starting the Ollama app manually.")


def ensure_model():
    models = get_models()
    if models is None:
        raise RuntimeError("Ollama disconnected. Start it and retry.")
    if any(entry.get("name") == MODEL for entry in models):
        return
    print(f"Downloading {MODEL}. The default model is about 1.9 GB; internet is needed once.", flush=True)
    request = Request(f"{URL}/api/pull", data=json.dumps({"model": MODEL, "stream": True}).encode(),
                      headers={"Content-Type": "application/json"})
    last_status = None
    with urlopen(request, timeout=120) as response:
        for line in response:
            update = json.loads(line)
            if update.get("error"):
                raise RuntimeError(update["error"])
            status = update.get("status", "Downloading")
            if update.get("total"):
                percentage = int(update.get("completed", 0) / update["total"] * 100)
                status = f"{status}: {percentage // 5 * 5}%"
            if status != last_status:
                print(status, flush=True)
                last_status = status
    if not any(entry.get("name") == MODEL for entry in get_models() or []):
        raise RuntimeError("The model download did not complete. Check the connection and run again; downloads resume.")


def main():
    os.chdir(ROOT)
    process = None
    try:
        executable = setup_python()
        process = ensure_ollama()
        ensure_model()
        print("Opening ReceiptCheck at http://localhost:8501 — keep this window open.", flush=True)
        return subprocess.call([str(executable), "-m", "streamlit", "run", str(ROOT / "app.py"), *sys.argv[1:]])
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"\nReceiptCheck could not start: {exc}", file=sys.stderr)
        return 1
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    sys.exit(main())
