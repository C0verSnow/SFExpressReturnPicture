"""Remote regression checks for source layout and existing source-tree entry points."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import address_to_html
import full_page_to_html
import prepare_pages
import split_screenshot
import workflow
from sf_return import cli, paths
from sf_return.images import split
from sf_return.render import address_panel, full_page, pages


class LayoutTests(unittest.TestCase):
    def test_legacy_exports_point_at_package_implementations(self):
        for legacy, current, names in (
            (address_to_html, address_panel, ('load_address', 'export_address')),
            (full_page_to_html, full_page, ('export_page',)),
            (prepare_pages, pages, ('prepare_pages',)),
            (split_screenshot, split, ('find_gray_panel', 'split_screenshot')),
            (workflow, cli, ('main', 'run_check')),
        ):
            for name in names:
                with self.subTest(module=legacy.__name__, export=name):
                    self.assertIs(getattr(legacy, name), getattr(current, name))
        for legacy in (address_to_html, full_page_to_html, prepare_pages, workflow):
            self.assertEqual(legacy.ROOT, paths.ROOT)

    def test_resource_paths_preserve_source_and_license_files(self):
        self.assertEqual(paths.ROOT, Path(__file__).resolve().parents[1])
        for resource in (
            paths.SOURCE_IMAGE, paths.DEFAULT_CONFIG,
            paths.FONTS / 'NotoSansCJKsc-Regular.otf', paths.FONTS / 'OFL.txt',
            paths.TEMPLATES / 'full-page.html', paths.TEMPLATES / 'full-page.js',
            paths.TEMPLATES / 'address.js', paths.ADDRESS / 'contact.js',
            paths.REGIONS / 'list.json', paths.REGIONS / 'LICENSE',
        ):
            with self.subTest(resource=resource):
                self.assertTrue(resource.is_file(), resource)

    def test_legacy_cli_help_works_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            for script in ('workflow.py', 'address_to_html.py', 'full_page_to_html.py',
                           'prepare_pages.py', 'split_screenshot.py'):
                with self.subTest(script=script):
                    result = subprocess.run(
                        [sys.executable, str(paths.ROOT / script), '--help'],
                        cwd=directory, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('usage:', result.stdout)
            self.assertEqual(list(Path(directory).iterdir()), [])
