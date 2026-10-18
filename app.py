"""ReceiptCheck: connect Excel once, upload receipts, let local AI do the entry."""

import time

import streamlit as st

from receiptcheck import (
    DATA, ROOT, OLLAMA_URL, ReceiptError, connect_workbook, extract_receipt,
    installed_models, model_ready, prepare_image, read_receipts, receipt_id, record_receipt, saved_connection,
)
from model_settings import preferred_model, save_model


@st.cache_data(ttl=30, max_entries=8, show_spinner=False)
def discover_models(server):
    return installed_models()

st.set_page_config(page_title="ReceiptCheck · Receipts to Excel", page_icon="🧾", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1120px; padding-top: 2.8rem;}
h1 {letter-spacing: -.045em; font-size: 3.3rem !important;}
[data-testid="stMetric"] {background: #edf1eb; border-radius: 12px; padding: 16px;}
[data-testid="stFileUploader"] {border: 1px dashed #9bb7a7; border-radius: 14px; padding: 12px;}
</style>""", unsafe_allow_html=True)

DATA.mkdir(exist_ok=True)
initial_model = preferred_model(DATA)
st.session_state.setdefault("receipt_model", initial_model)
workbook = saved_connection()

with st.sidebar:
    st.markdown("### 🧾 ReceiptCheck")
    st.caption("Your receipts. Your laptop. Your spreadsheet.")
    st.divider()
    st.markdown("**Excel connection**")
    if workbook:
        st.success("Workbook connected")
        st.caption(str(workbook))
    else:
        st.info("Connect a workbook to get started.")
    with st.expander("Change workbook" if workbook else "Connect your workbook", expanded=not workbook):
        with st.form("connection"):
            location = st.text_input("Workbook path on this laptop", value=str(workbook or DATA / "receipts.xlsx"))
            st.caption("Choose a new file or an existing plain .xlsx workbook. We add Receipts and Line Items tabs. Close Excel while uploading.")
            if st.form_submit_button("Connect workbook", type="primary", width="stretch"):
                try:
                    connect_workbook(location)
                    st.rerun()
                except (ReceiptError, OSError) as exc:
                    st.error(str(exc))
    st.divider()
    st.markdown("**AI model**")
    if st.button("Refresh models"):
        discover_models.clear()
    try:
        models = discover_models(OLLAMA_URL)
        discovery_error = None
    except ReceiptError as exc:
        models, discovery_error = [], str(exc)
    # Retain a removed/offline selection so it is never silently replaced.
    options = sorted(set(models + [st.session_state.receipt_model]))
    model = st.selectbox("Ollama model", options, key="receipt_model",
                         help="Choose an installed vision model. Your choice is remembered on this laptop.")
    ready, readiness_message = (False, discovery_error) if discovery_error else model_ready(model)
    if ready and model != initial_model:
        try:
            save_model(DATA, model)
        except OSError:
            st.warning("Using this model for this session, but could not save the preference. Check the data folder permissions.")
    if ready:
        st.caption(f"● Ready · {model}")
    else:
        st.warning(readiness_message)
    with st.expander("Add another model"):
        st.caption("Install a vision model in a terminal, then click Refresh models and select it above. For example:")
        st.code("ollama pull qwen3-vl:4b", language="bash")
        st.caption("Larger models need more memory. Custom models imported into Ollama also appear here. Text-only and cloud models cannot be used.")
    with st.expander("About your data"):
        st.caption("Receipt processing runs locally through Ollama. Receipt images and connection settings are saved in this project's data folder. No receipt is sent to a paid or cloud AI API.")
        st.caption("Recorded means the required fields are present and arithmetic checks passed. It does not guarantee that every character was read correctly.")

st.caption("LOCAL AI  /  AUTOMATIC BOOKKEEPING ENTRY")
st.title("Receipts in. Spreadsheet updated.")
st.markdown("Connect Excel once. Drop in a receipt. We read the details, check the numbers, and add the entry automatically.")

if not workbook:
    st.info("Start with **Connect your workbook** in the sidebar. A new workbook can be created for you.")

uploaded = st.file_uploader(
    "Upload receipt photos", type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True, disabled=not (workbook and ready),
    help="Printed receipts work best. Up to 10 MB per image. Extraction starts automatically after upload.",
)

demo = st.button("Try the included sample receipt", disabled=not (workbook and ready))
pending = [(file.name, file.getvalue()) for file in uploaded or []]
if demo:
    pending.append(("sample-receipt.png", (ROOT / "examples" / "sample-receipt.png").read_bytes()))

if "results" not in st.session_state:
    st.session_state.results = {}

if workbook and ready and pending:
    try:
        known_ids = {row["Receipt ID"] for row in read_receipts(workbook)}
    except ReceiptError as exc:
        st.error(str(exc))
        known_ids = None
    if known_ids is not None:
        for filename, content in pending:
            key = f"{workbook}:{receipt_id(content)}"
            if key in st.session_state.results:
                continue
            if receipt_id(content) in known_ids:
                st.session_state.results[key] = {"filename": filename, "status": "Duplicate skipped", "notes": []}
                continue
            started = time.monotonic()
            with st.status(f"Reading {filename}…", expanded=True) as progress:
                stage_bar = st.progress(0, text="Step 1 of 4 · Preparing image")
                st.caption("Progress shows completed steps, not time remaining. Reading is usually the longest step.")
                activity = st.empty()

                def show_activity(stage, updates):
                    if stage == "validating":
                        stage_bar.progress(50, text="Step 3 of 4 · Checking extracted details")
                        activity.caption("Model response received. Checking the receipt structure and amounts…")
                    elif updates == 1 or updates % 10 == 0:
                        activity.caption(f"Model is responding · {updates} response updates received")

                try:
                    image = prepare_image(content)
                    stage_bar.progress(25, text="Step 2 of 4 · Reading receipt with local AI")
                    activity.caption("Waiting for the first model response. Loading the model and reading the image can take several minutes on a CPU.")
                    with st.spinner(f"Processing with {model}", show_time=True):
                        receipt = extract_receipt(image, model, on_progress=show_activity)
                    stage_bar.progress(75, text="Step 4 of 4 · Saving to Excel")
                    activity.caption("Checking line calculations and updating your workbook…")
                    _, status, notes = record_receipt(workbook, receipt, content, filename, image)
                    known_ids.add(receipt_id(content))
                    st.session_state.results[key] = {"filename": filename, "status": status, "notes": notes,
                                                     "seconds": round(time.monotonic() - started, 1)}
                    stage_bar.progress(100, text="Complete · Excel updated")
                    activity.caption(f"Finished in {time.monotonic() - started:.1f}s")
                    progress.update(label=f"{filename} · {status}", state="complete", expanded=False)
                except (ReceiptError, OSError) as exc:
                    st.session_state.results[key] = {"filename": filename, "status": "Not saved", "notes": [str(exc)]}
                    activity.caption(f"Stopped after {time.monotonic() - started:.1f}s · No entry saved")
                    progress.update(label=f"{filename} · Not saved", state="error", expanded=True)

results = [result for key, result in st.session_state.results.items() if workbook and key.startswith(f"{workbook}:")]
for result in results:
    label = f"{result['filename']} — {result['status']}"
    if result["status"] == "Not saved":
        st.error(label + ": " + " ".join(result["notes"]))
    elif result["status"] == "Needs review":
        st.warning(label + ". Saved with review notes: " + " ".join(result["notes"]))
    elif result["status"] == "Duplicate skipped":
        st.info(label + ". This exact image is already in the workbook.")
    else:
        st.success(label + f" · Excel updated in {result.get('seconds', 0)}s")

if any(result["status"] == "Not saved" for result in results):
    if st.button("Retry failed uploads"):
        st.session_state.results = {key: result for key, result in st.session_state.results.items()
                                    if result["status"] != "Not saved"}
        st.rerun()

st.divider()
st.subheader("Your receipt ledger")
if workbook:
    try:
        records = read_receipts(workbook)
        left, middle, right = st.columns(3)
        left.metric("Receipts saved", len(records))
        middle.metric("Checks passed", sum(row["Status"] == "Recorded" for row in records))
        right.metric("Needs review", sum(row["Status"] == "Needs review" for row in records))
        if records:
            columns = ["Source file", "Vendor", "Date", "Currency", "Total", "Status", "Review notes"]
            st.dataframe([{column: row[column] for column in columns} for row in reversed(records)],
                         hide_index=True, width="stretch")
            st.download_button("Download workbook snapshot", workbook.read_bytes(), file_name=workbook.name,
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.caption("The connected file is already updated. This download is optional. Check the Line Items tab for item details.")
        else:
            st.caption("Your first upload will appear here automatically.")
    except (ReceiptError, OSError) as exc:
        st.error(str(exc))
else:
    st.caption("Connect a workbook to see your entries here.")

st.caption("Printed receipt photos · Local open-weight vision model · MIT-licensed app")
