"""Remote CI: serve the actual deployment directory and edit/download over HTTP."""
import functools
import io
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'pages' if (ROOT / 'pages/index.html').exists() else ROOT / 'pages-site'
OUT = ROOT / 'pages-check'
OUT.mkdir()
server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=str(SITE)))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        errors, external = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url)
                if request.url.startswith(('http:', 'https:')) and not request.url.startswith(base + '/') else None)
        assert page.goto(base + '/').status == 200
        page.wait_for_function("!document.getElementById('edit-address').disabled")
        assert page.title() == '退货退款详情 · 收件信息编辑'
        assert page.evaluate("document.fonts.check('48px Address', '新商家')")
        for filename in ('full-page.js', 'address-dialog.svg', 'NotoSansCJKsc-Regular.otf', 'OFL.txt', 'address.json'):
            response = page.request.get(base + '/' + filename)
            assert response.status == 200, filename
            assert response.body() == (SITE / filename).read_bytes(), filename
        assert page.request.get(base + '/404.html').status == 200
        page.locator('#edit-address').click()
        page.locator('#merchant-input').fill('新商家')
        page.locator('#phone-input').fill('13800138000')
        page.locator('#address-input').fill('上海市浦东新区\n新地址 100 号')
        with page.expect_download() as pending:
            page.locator('#confirm').click()
        pending.value.save_as(OUT / 'edited.png')
        assert pending.value.suggested_filename == 'return-page-edited.png'
        page.wait_for_function("!document.getElementById('editor').open")
        page.locator('#page').screenshot(path=str(OUT / 'preview.png'))
        with Image.open(OUT / 'edited.png') as photo, Image.open(OUT / 'preview.png') as preview:
            assert photo.size == (1182, 2560)
            assert ImageChops.difference(photo.convert('RGB'), preview.convert('RGB')).getbbox() is None
        with page.expect_download() as pending:
            page.locator('#save-json').click()
        pending.value.save_as(OUT / 'address.json')
        assert json.loads((OUT / 'address.json').read_text()) == {
            'merchant': '新商家', 'phone': '13800138000', 'lines': ['上海市浦东新区', '新地址 100 号', '']}
        with page.expect_download() as pending:
            page.locator('#save').click()
        pending.value.save_as(OUT / 'edited.html')
        # A saved page must still work away from the deployed site.
        page.context.set_offline(True)
        page.goto((OUT / 'edited.html').as_uri())
        page.wait_for_function("!document.getElementById('edit-address').disabled")
        with page.expect_download() as pending:
            page.locator('#save-photo').click()
        pending.value.save_as(OUT / 'reopened.png')
        assert (OUT / 'reopened.png').read_bytes() == (OUT / 'edited.png').read_bytes()
        page.locator('#edit-address').click()
        assert page.locator('#merchant-input').input_value() == '新商家'
        assert not errors, errors
        assert not external, external
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join()
