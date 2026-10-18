"""Run the actual local model against the included sample and verify Excel output."""
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import receiptcheck as rc

content = (rc.ROOT / "examples" / "sample-receipt.png").read_bytes()
started = time.monotonic()
receipt = rc.extract_receipt(rc.prepare_image(content))
print(receipt.model_dump_json(indent=2))
print(f"Extraction time: {time.monotonic() - started:.1f}s")
assert receipt.vendor and "LAHORE" in receipt.vendor.upper(), "Vendor was not read correctly"
assert receipt.date and receipt.date.isoformat() == "2026-10-18", "Date mismatch"
assert receipt.currency and receipt.currency.upper() == "PKR", "Currency mismatch"
assert receipt.total == 660, "Total mismatch"
assert len(receipt.items) == 2, "Line-item count mismatch"
assert sorted(item.line_total for item in receipt.items) == [100, 500], "Line-item amount mismatch"
assert not rc.review_reasons(receipt), rc.review_reasons(receipt)
with tempfile.TemporaryDirectory() as temporary:
    folder = Path(temporary)
    with patch.object(rc, "DATA", folder / "data"):
        path = rc.connect_workbook(str(folder / "demo.xlsx"))
        assert rc.record_receipt(path, receipt, content, "sample-receipt.png", rc.prepare_image(content))[0]
        assert not rc.record_receipt(path, receipt, content, "sample-receipt.png", rc.prepare_image(content))[0]
        assert len(rc.read_receipts(path)) == 1
print("PASS: real model → validated data → Excel → duplicate protection")
