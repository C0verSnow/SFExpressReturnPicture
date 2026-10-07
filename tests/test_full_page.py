import json
import tempfile
import unittest
from pathlib import Path

from full_page_to_html import export_page
from address_to_html import ROOT


class FullPageTests(unittest.TestCase):
    def test_embedded_resources_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'page'
            page = export_page(ROOT / 'address.json', output)
            original = page.read_bytes()
            self.assertIn(b'data:image/png;base64,', original)
            self.assertIn(b'data:font/otf;base64,', original)
            for name in ('full-page.js', 'address-dialog.svg', 'NotoSansCJKsc-Regular.otf', 'OFL.txt'):
                self.assertTrue((output / name).is_file())
            with self.assertRaises(ValueError):
                export_page(ROOT / 'address.json', output)
            self.assertEqual(page.read_bytes(), original)

    def test_invalid_address_and_script_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'config.json'
            output = Path(directory) / 'output'
            for data in ([], {'merchant': '其他'},
                         {'merchant': '', 'phone': '123', 'lines': ['地址']},
                         {'merchant': '新商家', 'phone': '123\n456', 'lines': ['地址']},
                         {'merchant': 123, 'phone': '456', 'lines': ['地址']},
                         {'merchant': '多联科技', 'phone': '18925023056', 'lines': ['']}):
                config.write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaises(ValueError):
                    export_page(config, output)
                self.assertFalse(output.exists())
            config.write_text(json.dumps({'merchant': '新商家', 'phone': '13800138000',
                                          'lines': ['</script><script>alert(1)</script>']}), encoding='utf-8')
            page = export_page(config, output).read_text()
            self.assertNotIn('</script><script>alert(1)', page)
            self.assertIn('\\u003c/script', page)
            exported = json.loads((output / 'address.json').read_text())
            self.assertEqual(exported['merchant'], '新商家')
            self.assertEqual(exported['phone'], '13800138000')
            self.assertEqual(exported['lines'][1:], ['', ''])
