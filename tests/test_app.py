"""UI tests explicitly mock the model; no GPU or download is required."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import streamlit as st

import receiptcheck as rc
from model_settings import preferred_model
from test_receiptcheck import sample


class AppTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        discovery = patch.object(rc, "installed_models", return_value=[rc.DEFAULT_MODEL, "my-receipt-model:latest"])
        discovery.start()
        self.addCleanup(discovery.stop)

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
                app.selectbox(key="receipt_model").select("my-receipt-model:latest").run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(preferred_model(rc.DATA), "my-receipt-model:latest")
                next(button for button in app.button if button.label == "Try the included sample receipt").click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(rc.read_receipts(connected)), 1)
                self.assertEqual(extraction.call_count, 1)
                self.assertEqual(extraction.call_args.args[1], "my-receipt-model:latest")
                fresh = AppTest.from_file(str(rc.ROOT / "app.py"), default_timeout=15).run()
                self.assertEqual(fresh.selectbox(key="receipt_model").value, "my-receipt-model:latest")
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

    def test_refresh_discovers_models_without_replacing_missing_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(rc, "DATA", Path(temporary) / "data"), \
                    patch.object(rc, "installed_models", return_value=[rc.DEFAULT_MODEL]) as discovery, \
                    patch.object(rc, "model_ready", return_value=(True, "Ready")) as readiness:
                app = AppTest.from_file(str(rc.ROOT / "app.py"), default_timeout=15).run()
                discovery.return_value = [rc.DEFAULT_MODEL, "new-vision:latest"]
                next(b for b in app.button if b.label == "Refresh models").click().run()
                self.assertIn("new-vision:latest", app.selectbox[0].options)
                app.selectbox[0].select("new-vision:latest").run()
                discovery.return_value = [rc.DEFAULT_MODEL]
                readiness.return_value = (False, "Model not installed")
                next(b for b in app.button if b.label == "Refresh models").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox[0].value, "new-vision:latest")
                self.assertTrue(any("Model not installed" in w.value for w in app.warning))
                self.assertEqual(preferred_model(rc.DATA), "new-vision:latest")

    def test_offline_discovery_can_recover_and_invalid_model_is_not_saved(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(rc, "DATA", Path(temporary) / "data"), \
                    patch.object(rc, "installed_models", side_effect=rc.ReceiptError("Start Ollama")) as discovery, \
                    patch.object(rc, "model_ready", return_value=(False, "This model cannot read receipt images")):
                app = AppTest.from_file(str(rc.ROOT / "app.py"), default_timeout=15).run()
                self.assertFalse(app.exception)
                self.assertTrue(any("Start Ollama" in w.value for w in app.warning))
                discovery.side_effect = None
                discovery.return_value = [rc.DEFAULT_MODEL, "text-only:latest"]
                next(b for b in app.button if b.label == "Refresh models").click().run()
                app.selectbox[0].select("text-only:latest").run()
                self.assertFalse(app.exception)
                self.assertTrue(any("cannot read" in w.value for w in app.warning))
                self.assertFalse((rc.DATA / "model.json").exists())
