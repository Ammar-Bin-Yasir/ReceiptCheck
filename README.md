# ReceiptCheck

**Connect a local Excel workbook once. Upload a receipt. Let local, open-weight AI enter the details.**

Built for Hacktoberfest Hack Day Lahore × Fluxxion, Best Open-Source AI Project.

ReceiptCheck extracts printed receipts into a real `.xlsx` workbook automatically. It adds vendor, date, currency, amounts and line items, checks arithmetic, and labels incomplete or inconsistent entries **Needs review**. There is no API key, paid inference API, or mandatory export step.

## Windows: run on your friend's laptop

1. Install **64-bit Python 3.12** from [python.org](https://www.python.org/downloads/). Select **Add python.exe to PATH** in the installer.
2. Install [Ollama for Windows](https://ollama.com/download/windows). Open Ollama once after installation. Use a current graphics driver for GPU acceleration.
3. Download this repository as a ZIP and **extract it** into a writable folder, or clone it. Do not copy a Linux `.venv` folder onto Windows.
4. Double-click **`run.bat`**. Keep the console open. The first run installs dependencies and downloads `qwen3-vl:2b` (approximately 1.9 GB). Later runs reuse both.
5. Open **http://localhost:8501** if a browser does not open automatically.
6. In the sidebar, choose a path such as `C:\Users\YourName\Documents\receipts.xlsx`, then click **Connect workbook**. A new file is created if it does not exist.
7. Drop a receipt image into the uploader. Extraction and workbook updates happen automatically.

Use **Try the included sample receipt** for a first test. It is explicitly synthetic; it goes through the actual model, not a prefilled response.

## Linux

Install Python 3.11+ (3.12 recommended), its `venv` support, and [Ollama](https://ollama.com/download/linux), then run:

```bash
bash run.sh
```

On Ubuntu/Debian, install `python3-venv` if Python reports that `ensurepip` is unavailable. The launcher starts Ollama if needed, downloads the model if missing, installs Python packages in `.venv`, and starts Streamlit. Project paths containing spaces are supported.

## After upload

1. The app validates and rotates the image, then sends it to the local Ollama server.
2. The selected vision model extracts a constrained JSON receipt structure. Missing or unreadable values remain blank.
3. Python checks the structure and line calculations, subtotal, tax, discount and total using decimal arithmetic.
4. Receipt and item rows are saved together, with review status and notes. The existing workbook is backed up before replacement.
5. The dashboard shows the saved entries. Downloading a workbook snapshot is optional; the selected file is already updated.

No confirmation is required for normal uploads. Entries that fail checks are saved as **Needs review**, with an explanation. Extraction or file-write failures are shown as **Not saved** and can be retried.

During extraction, a progress bar tracks four steps: preparing the image, reading it, checking the result, and saving to Excel. An elapsed-time spinner stays visible while waiting for the model, and a live response-update count shows when the model starts responding. The bar measures completed steps, not estimated time: reading can take several minutes on a CPU, especially for the first receipt. Interrupted or invalid model responses are never saved, and failed operations do not show 100% completion.

**Recorded means checks passed, not that extraction is guaranteed correct.** A model can misread multiple values consistently. Review the ledger before using it for accounting decisions. This app performs data entry, not complete bookkeeping or tax filing.

## Excel behavior

- **Receipts:** one row per receipt, with ID, source, date, vendor, currency, amounts, status and review notes.
- **Line Items:** item descriptions, quantities, prices and amounts, linked to the receipt ID.
- Existing sheets, ordinary cell values, formulas and formatting are retained. Use a standard, unencrypted `.xlsx`; macros and advanced features such as embedded controls are outside this demo's scope.
- Existing `Receipts` or `Line Items` tabs must have this app's column layout. Conflicts produce an error rather than overwrite data. The app manages these two tabs; use other tabs for personal formulas and notes.
- A `.xlsx.bak` file beside the workbook holds the previous version. Stop the app before restoring a backup.
- **Close the workbook in Excel while uploading**, particularly on Windows. If Excel locks it, close Excel and click **Retry failed uploads**.
- Exact duplicate images are skipped, including after app restarts. Different photos of the same receipt are not reliably deduplicated.
- Use one app instance per workbook. Concurrent Excel editing or several app processes writing the same file are not supported.
- Extracted text starting with `=` is stored as literal text, not as an Excel formula.

## Privacy and storage

The browser, app, Ollama and workbook run on the same laptop. By default the app listens only on `127.0.0.1`; this is not a public hosted service.

- `data/connection.json`: saved workbook location.
- `data/model.json`: saved model choice, shared by the app and launcher.
- `data/receipts/`: normalized receipt images for traceability.
- Workbook: the path chosen by the user.
- `.runtime/ollama.log`: diagnostics when the launcher starts Ollama.
- Model weights: Ollama's model directory, or your configured `OLLAMA_MODELS`.

First setup needs internet for software and model downloads. Extraction works offline afterward. Receipt images, environments and workbooks are excluded from Git. Do not publish personal receipt data.

## Model and hardware

Default: [`qwen3-vl:2b`](https://ollama.com/library/qwen3-vl:2b), a quantized open-weight vision model. The [upstream model](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) uses Apache 2.0. Application code is MIT-licensed; model weights retain their own license. Install current Ollama (0.12.7 or newer is required for this model).

A GPU is not strictly required: Ollama can use the CPU, but image processing can be slow. A supported GPU and sufficient RAM/VRAM improve usability. Test representative receipts on the actual demo laptop. The app allows up to ten minutes per extraction before reporting a timeout.

### Choose your own model

Use **AI model → Ollama model** in the sidebar to choose an installed model. The app checks that it supports images before enabling uploads. Valid choices are saved automatically and reused after restarting, including by the launcher. Custom vision models imported into Ollama are supported; text-only and Ollama cloud models are rejected.

To add a model, install it in a terminal on the laptop running the app, then click **Refresh models** and select it. For example, for a larger model on a capable laptop:

```text
ollama pull qwen3-vl:4b
```

The dropdown lists installed models; compatibility is checked when selected. An unavailable or incompatible choice disables processing and does not replace your saved valid preference. Switching models applies to subsequent extractions; it does not reprocess receipts already saved. Extraction accuracy and memory needs vary by model. Try the included sample after switching.

For the **first launch**, before a preference is saved, you can also set the initial model on Windows:

```bat
set RECEIPTCHECK_MODEL=qwen3-vl:4b
run.bat
```

Linux:

```bash
RECEIPTCHECK_MODEL=qwen3-vl:4b bash run.sh
```

The launcher downloads the saved model (or the environment/default model if no choice is saved) if missing. A saved sidebar choice takes precedence over `RECEIPTCHECK_MODEL`. `OLLAMA_URL` can select an existing server; a remote URL sends receipt images there and is no longer fully local.

## Tests

After dependencies are installed, Windows:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\smoke_extract.py
```

Linux:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/smoke_extract.py
```

Unit and Streamlit workflow tests need no GPU or Ollama; UI tests explicitly mock extraction. They cover workbook preservation, failed saves, arithmetic checks, literal text, duplicate detection, persistent connection, model selection and startup behavior. GitHub Actions is configured for Windows and Linux with Python 3.11 and 3.12.

`smoke_extract.py` separately runs the **real model** on the sample and verifies vendor, date, currency, total, line amounts, Excel output and duplicate prevention. It uses your saved model choice, falling back to the environment/default model. Run it with Ollama active. It uses a temporary workbook and leaves the connected workbook alone. A failed assertion means extraction did not match the sample; it is not replaced with fake data.

Suggested demo: connect a workbook, upload the sample, show both Excel tabs, then upload the identical image again. Follow with a real printed receipt. A teammate can compare the extracted fields with the originals.

Current scope: PNG, JPEG and WebP images, up to 10 MB and 20 megapixels each; printed receipts first. PDF ingestion, guaranteed handwriting accuracy, payment matching, full bookkeeping and cloud Excel connections are not implemented.
