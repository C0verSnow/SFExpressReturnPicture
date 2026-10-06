import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from split_screenshot import find_gray_panel, split_screenshot


class ScreenshotTests(unittest.TestCase):
    def screenshot(self):
        image = Image.new("RGB", (200, 500), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 200, 189, 349), fill=(246, 246, 246))
        draw.rectangle((20, 230, 70, 245), fill="black")
        draw.rectangle((10, 400, 189, 405), fill=(246, 246, 246))
        return image

    def test_auto_panel_and_lossless_reassembly(self):
        image = self.screenshot()
        self.assertEqual(find_gray_panel(image), (200, 350))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            image.save(source)
            paths, boundaries = split_screenshot(source, Path(directory) / "result")
            self.assertEqual(boundaries, (200, 350))
            rebuilt = Image.new("RGB", image.size)
            offset = 0
            for path, expected_height in zip(paths, (200, 150, 150)):
                with Image.open(path) as part:
                    self.assertEqual(part.format, "PNG")
                    self.assertEqual(part.size, (200, expected_height))
                    rebuilt.paste(part, (0, offset))
                    offset += part.height
            self.assertEqual(rebuilt.tobytes(), image.tobytes())

    def test_multiple_panels_and_missing_panel(self):
        with self.assertRaises(ValueError):
            find_gray_panel(Image.new("RGB", (200, 500), "white"))
        image = self.screenshot()
        ImageDraw.Draw(image).rectangle((10, 30, 189, 100), fill=(246, 246, 246))
        with self.assertRaises(ValueError):
            find_gray_panel(image)

    def test_manual_boundaries_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            Image.new("RGB", (100, 300), "white").save(source)
            output = Path(directory) / "out"
            for top, bottom in ((0, 200), (100, 300), (200, 100), (100, None)):
                with self.assertRaises(ValueError):
                    split_screenshot(source, output, top, bottom)
                self.assertFalse(output.exists())
            paths, _ = split_screenshot(source, output, 100, 200)
            before = paths[0].read_bytes()
            with self.assertRaises(ValueError):
                split_screenshot(source, output, 50, 150)
            self.assertEqual(paths[0].read_bytes(), before)

    def test_cli_failure_does_not_create_output(self):
        script = Path(__file__).resolve().parents[1] / "split_screenshot.py"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            result = subprocess.run(
                [sys.executable, str(script), str(Path(directory) / "missing.png"),
                 "--output-dir", str(output)], capture_output=True, text=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("切图失败", result.stderr)
            self.assertFalse(output.exists())

    def test_repository_sample(self):
        source = Path(__file__).resolve().parents[1] / "2026-10-06 11.08.30.jpg"
        with Image.open(source) as image:
            top, bottom = find_gray_panel(image)
            # Address panel in the supplied 1182 x 2560 screenshot.
            self.assertTrue(1600 < top < 1680, (top, bottom))
            self.assertTrue(2080 < bottom < 2130, (top, bottom))
        with tempfile.TemporaryDirectory() as directory:
            paths, _ = split_screenshot(source, directory)
            with Image.open(source) as original:
                rebuilt = Image.new("RGB", original.size)
                offset = 0
                for path in paths:
                    with Image.open(path) as part:
                        rebuilt.paste(part, (0, offset))
                        offset += part.height
                self.assertEqual(offset, original.height)
                self.assertEqual(rebuilt.tobytes(), original.convert("RGB").tobytes())


if __name__ == "__main__":
    unittest.main()
