"""Package only source and synthetic examples; never ship private runtime data."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
output = root / "dist" / "ReceiptCheck-source.zip"
output.parent.mkdir(exist_ok=True)
files = [root / name for name in [
    "app.py", "receiptcheck.py", "model_settings.py", "launcher.py", "run.sh", "run.bat", "requirements.txt",
    "README.md", "LICENSE", ".gitignore", ".gitattributes",
]]
for directory, pattern in [("tests", "*.py"), ("scripts", "*.py"), ("examples", "*.png"),
                           (".streamlit", "*.toml"), (".github/workflows", "*.yml")]:
    files.extend(sorted((root / directory).glob(pattern)))
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        data = path.read_bytes()
        if path.suffix == ".bat":
            data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        archive.writestr("ReceiptCheck/" + path.relative_to(root).as_posix(), data)
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
print(f"{output} ({output.stat().st_size:,} bytes, {len(files)} files)")
