"""Model preference shared by the app and the dependency-free launcher."""
import json
import os
from pathlib import Path
import tempfile

DEFAULT_MODEL = "qwen3-vl:2b"


def preferred_model(directory: Path) -> str:
    try:
        value = json.loads((directory / "model.json").read_text(encoding="utf-8"))
        model = value.get("model") if isinstance(value, dict) else None
        if isinstance(model, str) and model.strip():
            return model.strip()
    except (OSError, ValueError):
        pass
    return os.environ.get("RECEIPTCHECK_MODEL", "").strip() or DEFAULT_MODEL


def save_model(directory: Path, model: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                     suffix=".tmp", delete=False) as output:
        temporary = Path(output.name)
        json.dump({"model": model}, output)
    try:
        os.replace(temporary, directory / "model.json")
    finally:
        temporary.unlink(missing_ok=True)
