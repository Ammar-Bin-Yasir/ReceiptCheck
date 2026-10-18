import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

import receiptcheck as rc
from model_settings import preferred_model, save_model


class ModelTests(unittest.TestCase):
    def test_discovery_uses_installed_names_including_custom_models(self):
        response = Mock()
        response.json.return_value = {"models": [{"name": "custom/receipt:latest"}, {"name": rc.DEFAULT_MODEL}]}
        with patch.object(rc.requests, "get", return_value=response):
            self.assertEqual(rc.installed_models(), ["custom/receipt:latest", rc.DEFAULT_MODEL])
        with patch.object(rc.requests, "get", side_effect=requests.ConnectionError):
            with self.assertRaisesRegex(rc.ReceiptError, "Start Ollama"):
                rc.installed_models()

    def test_readiness_rejects_missing_text_and_cloud_models(self):
        response = Mock(status_code=200)
        with patch.object(rc.requests, "post", return_value=response) as post:
            response.json.return_value = {"capabilities": ["completion", "vision"]}
            self.assertTrue(rc.model_ready("custom:latest")[0])
            self.assertEqual(post.call_args.kwargs["json"], {"model": "custom:latest"})
            response.json.return_value = {"capabilities": ["completion"]}
            self.assertIn("cannot read", rc.model_ready("text:latest")[1])
            response.json.return_value = {"capabilities": ["vision"], "remote_host": "https://ollama.com"}
            self.assertIn("Cloud models", rc.model_ready("cloud:latest")[1])
            response.status_code = 404
            self.assertIn("ollama pull missing:latest", rc.model_ready("missing:latest")[1])

    def test_saved_model_survives_restart_and_failed_save_preserves_previous(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict("os.environ", {"RECEIPTCHECK_MODEL": "first:latest"}):
            directory = Path(temporary)
            self.assertEqual(preferred_model(directory), "first:latest")
            save_model(directory, "custom:latest")
            self.assertEqual(preferred_model(directory), "custom:latest")
            with patch("model_settings.os.replace", side_effect=PermissionError):
                with self.assertRaises(PermissionError):
                    save_model(directory, "other:latest")
            self.assertEqual(preferred_model(directory), "custom:latest")
            self.assertFalse(list(directory.glob("*.tmp")))
            for invalid in ["broken json", json.dumps([]), json.dumps({"model": 123})]:
                (directory / "model.json").write_text(invalid, encoding="utf-8")
                self.assertEqual(preferred_model(directory), "first:latest")
