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
SITE = ROOT / 'pages-site'
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
        page.locator('#address-input').fill('上海市\n浦东新区\n新地址 100 号')
        with page.expect_download() as pending:
            page.locator('#confirm').click()
        pending.value.save_as(OUT / 'edited.png')
        assert pending.value.suggested_filename == 'return-page-edited.png'
        page.wait_for_function("!document.getElementById('editor').open")
        # Compare downloaded full resolution with the displayed canvas pixels.
        import base64
        data = page.locator('#rendered-photo').evaluate("canvas => canvas.toDataURL().split(',')[1]")
        (OUT / 'preview.png').write_bytes(base64.b64decode(data))
        with Image.open(OUT / 'edited.png') as photo, Image.open(OUT / 'preview.png') as preview:
            assert photo.size == (1182, 2560)
            assert ImageChops.difference(photo.convert('RGB'), preview.convert('RGB')).getbbox() is None
        assert page.locator('#tools button').count() == 1
        assert page.locator('#license, #save, #save-json').count() == 0
        page.context.set_offline(True)
        with page.expect_download() as pending:
            page.locator('#save-photo').click()
        pending.value.save_as(OUT / 'offline.png')
        assert (OUT / 'offline.png').read_bytes() == (OUT / 'edited.png').read_bytes()
        assert not errors, errors
        assert not external, external
        browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join()
