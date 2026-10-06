import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from address_to_html import ROOT, export_address, load_address


class AddressExportTests(unittest.TestCase):
    def test_standalone_svg_text_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "page"
            page, svg = export_address(ROOT / "address.json", target)
            root = ET.fromstring(svg.read_text(encoding="utf-8"))
            self.assertEqual((root.attrib["width"], root.attrib["height"]), ("1182", "469"))
            texts = [node.text for node in root.findall("{http://www.w3.org/2000/svg}text")]
            self.assertIn("多联科技", texts)
            self.assertIn("18925023056", texts)
            source = page.read_text(encoding="utf-8")
            self.assertIn("data:font/otf;base64,", source)
            self.assertNotIn('<img', source)
            before = page.read_bytes()
            with self.assertRaises(ValueError):
                export_address(ROOT / "address.json", target)
            self.assertEqual(page.read_bytes(), before)

    def test_invalid_config_and_html_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            for data in ([], {}, {"merchant": "a", "phone": "b", "lines": ["a"]}):
                config.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_address(config)
            data = {"merchant": '<script>alert("x")</script>', "phone": "123",
                    "lines": ["甲&乙", "丙", "丁"]}
            config.write_text(json.dumps(data), encoding="utf-8")
            page, svg = export_address(config, Path(directory) / "out")
            self.assertIn('&lt;script&gt;', page.read_text(encoding="utf-8"))
            ET.fromstring(svg.read_text(encoding="utf-8"))
