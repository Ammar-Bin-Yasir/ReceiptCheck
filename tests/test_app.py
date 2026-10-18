"""UI tests explicitly mock the model; no GPU or download is required."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import receiptcheck as rc
from test_receiptcheck import sample


class AppTests(unittest.TestCase):
    def test_connect_once_sample_autosaves_and_duplicate_is_skipped(self):
        with tempfile.TemporaryDirectory(prefix="receipt check ") as temporary:
            with patch.object(rc, "DATA", Path(temporary) / "data"), \
                    patch.object(rc, "model_ready", return_value=(True, "Ready")), \
                    patch.object(rc, "extract_receipt", return_value=sample()) as extraction:
                app = AppTest.from_file(str(rc.ROOT / "app.py"), default_timeout=15).run()
                self.assertEqual(len(app.exception), 0)
                next(button for button in app.button if button.label == "Connect workbook").click().run()
                self.assertEqual(len(app.exception), 0)
                connected = rc.saved_connection()
                self.assertIsNotNone(connected)
                next(button for button in app.button if button.label == "Try the included sample receipt").click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(rc.read_receipts(connected)), 1)
                self.assertEqual(extraction.call_count, 1)
                fresh = AppTest.from_file(str(rc.ROOT / "app.py"), default_timeout=15).run()
                next(button for button in fresh.button if button.label == "Try the included sample receipt").click().run()
                self.assertEqual(len(fresh.exception), 0)
                self.assertEqual(len(rc.read_receipts(connected)), 1)
                self.assertEqual(extraction.call_count, 1)
                self.assertTrue(any("Duplicate skipped" in message.value for message in fresh.info))

    def test_unavailable_model_shows_setup_message(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(rc, "DATA", Path(temporary) / "data"), \
                    patch.object(rc, "model_ready", return_value=(False, "Start Ollama")):
                app = AppTest.from_file(str(rc.ROOT / "app.py"), default_timeout=15).run()
                self.assertEqual(len(app.exception), 0)
                self.assertTrue(any("Start Ollama" in warning.value for warning in app.warning))
                self.assertTrue(next(button for button in app.button if button.label == "Try the included sample receipt").disabled)
