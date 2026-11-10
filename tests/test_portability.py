"""Portable smoke tests for the platform-independent command scripts."""

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
LOADER = importlib.machinery.SourceFileLoader(
    "igc2gpx", str(SCRIPTS / "yuleshow-igc2gpx"))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
igc2gpx = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(igc2gpx)


class PortabilityTests(unittest.TestCase):
    def test_scripts_are_python_and_parse(self):
        for script in sorted(path for path in SCRIPTS.iterdir() if path.is_file()):
            with self.subTest(script=script.name):
                source = script.read_text(encoding="utf-8")
                self.assertTrue(source.startswith("#!/usr/bin/env python3"))
                compile(source, str(script), "exec")

    def test_igc_conversion_and_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "flight.IGC").write_text("flight", encoding="ascii")
            (folder / ".hidden.igc").write_text("flight", encoding="ascii")
            (folder / "existing.igc").write_text("flight", encoding="ascii")
            (folder / "existing.GPX").write_text("keep", encoding="ascii")
            calls = []
            real_run = subprocess.run

            def fake_run(command, check=False):
                if command[0] == "gpsbabel":
                    calls.append(command)
                    Path(command[-1]).write_text("<gpx/>", encoding="ascii")
                    return subprocess.CompletedProcess(command, 0)
                return real_run(command, check=check)

            with (mock.patch("pathlib.Path.cwd", return_value=folder),
                  mock.patch.object(igc2gpx.shutil, "which", return_value="gpsbabel"),
                  mock.patch.object(igc2gpx.subprocess, "run", side_effect=fake_run),
                  mock.patch.object(sys, "argv", ["yuleshow-igc2gpx"])):
                self.assertEqual(igc2gpx.main(), 0)

            self.assertEqual(len(calls), 2)
            self.assertTrue((folder / "flight.gpx").is_file())
            self.assertTrue((folder / ".hidden.gpx").is_file())
            self.assertEqual((folder / "existing.GPX").read_text(), "keep")
            self.assertTrue((folder / "existing.igc").is_file())

    def test_igc_publisher_does_not_overwrite_on_windows_or_unix(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "temporary.gpx"
            destination = folder / "flight.gpx"
            source.write_text("new", encoding="ascii")
            destination.write_text("original", encoding="ascii")
            if os.name == "nt":
                with self.assertRaises(FileExistsError):
                    igc2gpx.publish_without_overwrite(source, destination)
            else:
                with mock.patch.object(igc2gpx.subprocess, "run") as run:
                    run.return_value = subprocess.CompletedProcess([], 0)
                    self.assertFalse(igc2gpx.publish_without_overwrite(source, destination))
                    run.assert_called_once_with(
                        ["mv", "-n", str(source), str(destination)], check=False)
            self.assertEqual(destination.read_text(encoding="ascii"), "original")

    def test_rename_tools_handle_collisions(self):
        for script, source_name, target_name in (
                ("yuleshow-space2underscore", "two words", "two_words"),
                ("yuleshow-hyphen2underscore", "two-words", "two_words")):
            with self.subTest(script=script), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                (folder / source_name).write_text("source", encoding="ascii")
                (folder / target_name).write_text("target", encoding="ascii")
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS / script)], cwd=folder,
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual((folder / source_name).read_text(encoding="ascii"), "source")
                self.assertEqual((folder / target_name).read_text(encoding="ascii"), "target")

    def test_clean_help_is_available(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "yuleshow-clean"), "--help"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--dry-run", result.stdout)


if __name__ == "__main__":
    unittest.main()
