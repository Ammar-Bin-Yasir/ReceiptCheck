from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import launcher


class LauncherTests(unittest.TestCase):
    def test_platform_python_locations(self):
        self.assertEqual(launcher.python_in(Path("project with spaces/.venv"), "win32"),
                         Path("project with spaces/.venv/Scripts/python.exe"))
        self.assertEqual(launcher.python_in(Path(".venv"), "linux"), Path(".venv/bin/python"))

    def test_existing_server_and_model_need_no_process_or_download(self):
        with patch.object(launcher, "get_models", return_value=[{"name": launcher.MODEL}]), \
                patch.object(launcher.subprocess, "Popen") as spawn, \
                patch.object(launcher, "urlopen") as download:
            self.assertIsNone(launcher.ensure_ollama())
            launcher.ensure_model()
            spawn.assert_not_called()
            download.assert_not_called()

    def test_startup_failure_gives_actionable_error(self):
        with patch.object(launcher, "get_models", return_value=None), \
                patch.object(launcher.shutil, "which", return_value=None), \
                patch.object(launcher.sys, "platform", "linux"):
            with self.assertRaisesRegex(RuntimeError, "Install Ollama"):
                launcher.ensure_ollama()

    def test_failed_dependency_install_is_not_marked_complete(self):
        import subprocess
        with tempfile.TemporaryDirectory(prefix="receipt check ") as temporary:
            root = Path(temporary)
            environment = root / ".venv"
            executable = launcher.python_in(environment)
            executable.parent.mkdir(parents=True)
            executable.write_text("placeholder")
            (root / "requirements.txt").write_text("example==1\n")
            with patch.object(launcher, "ROOT", root), \
                    patch.object(launcher.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "pip")):
                with self.assertRaises(subprocess.CalledProcessError):
                    launcher.setup_python()
            self.assertFalse((environment / ".receiptcheck-requirements").exists())
