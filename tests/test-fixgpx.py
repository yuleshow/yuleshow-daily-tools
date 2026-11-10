"""Run with python3 tests/test-fixgpx.py -v."""

import importlib.machinery
import importlib.util
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "yuleshow-fixgpx"
LOADER = importlib.machinery.SourceFileLoader("fixgpx", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
fixgpx = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(fixgpx)
HEADER = '<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
ENDING = '</trkseg></trk></gpx>'


def point(latitude="34.1539223", seconds=0, longitude="-118.1082890"):
    return (f'<trkpt lat="{latitude}" lon="{longitude}">'
            f'<time>2026-10-22T01:{seconds // 60:02d}:{seconds % 60:02d}Z</time></trkpt>')


class FixGpxTests(unittest.TestCase):
    def test_local_filename(self):
        cases = (
            ("2026-10-22T01:20:45Z", "20261021_1820-LA.gpx"),
            ("2026-01-22T01:20:45Z", "20260121_1720-LA.gpx"),
            ("2026-10-21T18:20:45-07:00", "20261021_1820-LA.gpx"),
            ("2026-03-08T09:59:00Z", "20260308_0159-LA.gpx"),
            ("2026-03-08T10:00:00Z", "20260308_0300-LA.gpx"),
            ("2026-11-01T08:30:00Z", "20261101_0130-LA.gpx"),
            ("2026-11-01T09:30:00Z", "20261101_0130-LA.gpx"),
            ("2026-10-22T01:20:45", None),
            ("invalid", None),
            ("", None),
        )
        for timestamp, expected in cases:
            with self.subTest(timestamp=timestamp):
                content = point("35").replace("2026-10-22T01:00:00Z", timestamp)
                root = fixgpx.close_gpx((HEADER + content + ENDING).encode())[1]
                self.assertEqual(fixgpx.local_filename(root), expected)

    def test_timestamp_sources(self):
        time = '<time>2026-10-22T01:20:00Z</time>'
        for content in (
                f'<wpt lat="35" lon="-118">{time}</wpt>',
                f'<rte><rtept lat="35" lon="-118">{time}</rtept></rte>',
                f'<metadata>{time}</metadata><wpt lat="35" lon="-118"/>',
                f'{time}<wpt lat="35" lon="-118"/>'):
            with self.subTest(content=content):
                root = fixgpx.close_gpx(f'<gpx>{content}</gpx>'.encode())[1]
                self.assertEqual(fixgpx.local_filename(root), "20261021_1820-LA.gpx")
        content = HEADER + '<trkpt><time>invalid</time></trkpt>' + point("35") + ENDING
        root = fixgpx.close_gpx(content.encode())[1]
        self.assertEqual(fixgpx.local_filename(root), "20261021_1800-LA.gpx")

    def test_local_rename_collision(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                source = folder / "trip.gpx"
                content = HEADER + point("35") + ENDING
                source.write_text(content)
                destination = folder / "20261021_1800-LA.gpx"
                if symlink:
                    try:
                        destination.symlink_to(folder / "missing")
                    except (NotImplementedError, OSError):
                        self.skipTest("symlinks are unavailable")
                else:
                    destination.write_text("existing file")
                fixgpx.process(source, False)
                self.assertEqual(source.read_text(), content)
                if symlink:
                    self.assertTrue(destination.is_symlink())
                    self.assertFalse(destination.exists())
                else:
                    self.assertEqual(destination.read_text(), "existing file")

    def test_classification(self):
        cases = [
            (point(), True),
            (point("34.1546072") + point(seconds=60) + point(seconds=120), True),
            (point("34.1546072") + point(seconds=60), False),
            (point() + point("34.1546072", 60) + point(seconds=120), False),
            (point("35") + point(seconds=60) + point(seconds=120), False),
            (point("0"), False),
            (point("nan"), False),
            ('<trkpt lat="34"/>', False),
            ('', False),
        ]
        for content, expected in cases:
            with self.subTest(content=content):
                _, root = fixgpx.close_gpx((HEADER + content + ENDING).encode())
                self.assertEqual(fixgpx.is_home_only(root), expected)

    def test_wider_home_drift(self):
        coordinates = (
            ("34.1537828", "-118.1080730"),
            ("34.1537817", "-118.1081235"),
            ("34.1538927", "-118.1080025"),
            ("34.1533487", "-118.1079760"),
            ("34.1538313", "-118.1080813"),
            ("34.1541717", "-118.1082542"),
        )
        for latitude, longitude in coordinates:
            for seconds in (0, 180):
                with self.subTest(latitude=latitude, longitude=longitude, seconds=seconds):
                    content = point(latitude, seconds, longitude)
                    if seconds:
                        content = point() + '</trkseg><trkseg>' + content
                    _, root = fixgpx.close_gpx((HEADER + content + ENDING).encode())
                    self.assertTrue(fixgpx.is_home_only(root))

    def test_home_radius_boundary(self):
        for distance, expected in ((74.9, True), (75.1, False), (101, False)):
            with self.subTest(distance=distance):
                latitude = fixgpx.HOME_LATITUDE + math.degrees(distance / 6371008.8)
                content = point() + point(str(latitude), 180) + point(seconds=240)
                _, root = fixgpx.close_gpx((HEADER + content + ENDING).encode())
                self.assertEqual(fixgpx.is_home_only(root), expected)

    def test_closing_tags(self):
        for suffix in ("", "</trkseg>", "</trkseg></trk>", ENDING):
            original = (HEADER + point("35") + suffix).encode()
            repaired, _ = fixgpx.close_gpx(original)
            self.assertTrue(repaired.startswith(original))
            self.assertEqual(fixgpx.close_gpx(repaired)[0], repaired)
        prefixed = b'<g:gpx xmlns:g="http://www.topografix.com/GPX/1/1"><g:trk><g:trkseg>'
        self.assertTrue(fixgpx.close_gpx(prefixed)[0].endswith(b'</g:trkseg>\n</g:trk>\n</g:gpx>\n'))

    def test_repeated_closing_tags(self):
        for suffix in ("", ENDING, ENDING + ENDING):
            for latitude, home_only in (("34.1539223", True), ("35", False)):
                with self.subTest(suffix=suffix, latitude=latitude):
                    original = (HEADER + point() + ENDING + "\n"
                                + point(latitude, 60) + suffix).encode()
                    repaired, root = fixgpx.close_gpx(original)
                    points = root.findall('.//{*}trkpt')
                    self.assertEqual(len(points), 2)
                    self.assertEqual(points[1].attrib['lat'], latitude)
                    self.assertEqual(fixgpx.is_home_only(root), home_only)
                    self.assertEqual(fixgpx.close_gpx(repaired)[0], repaired)

    def test_valid_segments_unchanged(self):
        for separator in ('</trkseg><trkseg>', '</trkseg></trk><trk><trkseg>'):
            original = (HEADER + point() + separator + point("35") + ENDING).encode()
            repaired, root = fixgpx.close_gpx(original)
            self.assertEqual(repaired, original)
            self.assertFalse(fixgpx.is_home_only(root))

    def test_bad_xml_unchanged(self):
        for content in (HEADER + '<trkpt lat="34', HEADER + '<trkpt lat="34" lon="0">',
                        HEADER + '</wrong>', '<other/>', '', '<!DOCTYPE gpx><gpx/>',
                        HEADER + point() + ENDING + '<trkpt lat="34',
                        HEADER + point() + ENDING + HEADER + point() + ENDING):
            with self.subTest(content=content):
                with self.assertRaises((ValueError, fixgpx.expat.ExpatError)):
                    fixgpx.close_gpx(content.encode())

    def test_extra_locations_and_bad_times(self):
        content = '<gpx><wpt lat="35" lon="-118"/>' + HEADER.split('>', 1)[1] + point() + ENDING
        self.assertFalse(fixgpx.is_home_only(fixgpx.close_gpx(content.encode())[1]))
        for timestamps in ((0, 0, 120), (60, 0, 120)):
            content = point("34.1546072", timestamps[0])
            content += point(seconds=timestamps[1]) + point(seconds=timestamps[2])
            self.assertFalse(fixgpx.is_home_only(fixgpx.close_gpx((HEADER + content + ENDING).encode())[1]))

    def test_empty_recordings(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            empty_inputs = {
                "empty.gpx": HEADER + ENDING,
                "unfinished.gpx": HEADER,
                "root.gpx": '<gpx/>',
                "route.gpx": '<gpx><rte/></gpx>',
            }
            kept_inputs = {
                "waypoint.gpx": '<gpx><wpt lat="35" lon="-118"/></gpx>',
                "route-point.gpx": '<gpx><rte><rtept lat="35" lon="-118"/></rte></gpx>',
                "invalid-point.gpx": HEADER + '<trkpt/>' + ENDING,
                "zero-byte.gpx": '',
                "collision.gpx": HEADER + ENDING,
            }
            for name, content in {**empty_inputs, **kept_inputs}.items():
                (folder / name).write_text(content)
            (folder / "collision.bak").write_text("existing backup")
            command = [sys.executable, str(SCRIPT)]
            preview = subprocess.run(command + ["--dry-run"], cwd=folder, capture_output=True, text=True)
            self.assertEqual(preview.returncode, 1)
            self.assertEqual(preview.stdout.count("Would rename:"), len(empty_inputs))
            for name, content in {**empty_inputs, **kept_inputs}.items():
                self.assertEqual((folder / name).read_text(), content)
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout.count("Renamed:"), len(empty_inputs))
            for name, content in empty_inputs.items():
                self.assertFalse((folder / name).exists())
                expected, root = fixgpx.close_gpx(content.encode())
                self.assertTrue(fixgpx.is_empty(root))
                self.assertEqual((folder / name).with_suffix(".bak").read_bytes(), expected)
            for name, content in kept_inputs.items():
                self.assertEqual((folder / name).read_text(), content)
            self.assertEqual((folder / "collision.bak").read_text(), "existing backup")

    def test_recursive_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            nested = folder / "nested folder"
            nested.mkdir()
            inputs = {
                nested / ".home.GPX": HEADER + point(),
                folder / "trip & one.gpx": HEADER + point("35"),
                folder / "complete.gpx": HEADER + point("35", 120) + ENDING,
                folder / "collision.gpx": HEADER + point() + ENDING,
                folder / "broken.gpx": HEADER + '<trkpt lat="34',
                folder / "repeated-home.gpx": HEADER + point() + ENDING + point(seconds=60) + ENDING,
                folder / "repeated-trip.gpx": HEADER + point(seconds=60) + ENDING + point("35", 120) + ENDING,
            }
            for path, content in inputs.items():
                path.write_text(content)
            (folder / "collision.bak").write_text("keep me")
            symlinks_available = True
            try:
                (folder / "linked.gpx").symlink_to(nested / ".home.GPX")
            except (NotImplementedError, OSError):
                symlinks_available = False
            if sys.platform != "win32":
                (folder / "trip & one.gpx").chmod(0o640)
            command = [sys.executable, str(SCRIPT)]
            preview = subprocess.run(command + ["--dry-run"], cwd=folder, capture_output=True, text=True)
            self.assertEqual(preview.returncode, 1)
            self.assertIn("Would rename", preview.stdout)
            for path, content in inputs.items():
                self.assertEqual(path.read_text(), content)
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse((nested / ".home.GPX").exists())
            self.assertTrue((nested / ".home.bak").is_file())
            self.assertFalse((folder / "repeated-home.gpx").exists())
            for filename in ("repeated-home.bak", "20261021_1801-LA.gpx"):
                repaired = (folder / filename).read_bytes()
                unchanged, root = fixgpx.close_gpx(repaired)
                self.assertEqual(unchanged, repaired)
                self.assertEqual(len(root.findall('.//{*}trkpt')), 2)
            self.assertEqual((folder / "collision.bak").read_text(), "keep me")
            self.assertEqual((folder / "collision.gpx").read_text(), inputs[folder / "collision.gpx"])
            self.assertEqual((folder / "broken.gpx").read_text(), inputs[folder / "broken.gpx"])
            self.assertEqual((folder / "20261021_1802-LA.gpx").read_text(), inputs[folder / "complete.gpx"])
            for filename in ("complete.gpx", "repeated-trip.gpx", "trip & one.gpx"):
                self.assertFalse((folder / filename).exists())
            trip = folder / "20261021_1800-LA.gpx"
            if sys.platform != "win32":
                self.assertEqual(trip.stat().st_mode & 0o777, 0o640)
            self.assertTrue(trip.read_text().endswith("</gpx>\n"))
            if symlinks_available:
                self.assertTrue((folder / "linked.gpx").is_symlink())
            before = trip.read_bytes()
            subprocess.run(command, cwd=folder, capture_output=True)
            self.assertEqual(trip.read_bytes(), before)
            self.assertFalse(list(folder.glob(".yuleshow-fixgpx-*")))


if __name__ == "__main__":
    unittest.main()