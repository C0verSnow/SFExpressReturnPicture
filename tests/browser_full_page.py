"""Remote CI only: verify screenshot fidelity, modal editing and persistence."""
import json
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'offline-return-page'

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
    context.set_offline(True)
    page = context.new_page()
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    page.goto((OUT / 'return-page.html').as_uri())
    page.evaluate('document.fonts.ready')
    assert page.evaluate("document.fonts.check('48px Address', '新地址')")
    panel = page.locator('#page')
    assert panel.bounding_box() == {'x': 0, 'y': 0, 'width': 1182, 'height': 2560}
    panel.screenshot(path=str(OUT / 'initial.png'))
    with Image.open(ROOT / '2026-10-06 11.08.30.jpg') as source, Image.open(OUT / 'initial.png') as rendered:
        delta = ImageChops.difference(source.convert('RGB'), rendered.convert('RGB'))
        delta.save(OUT / 'initial-difference.png')
        assert delta.getbbox() is None, (delta.getbbox(), delta.getextrema(), rendered.size)
    page.locator('#edit-address').click()
    assert page.locator('#editor').is_visible()
    page.screenshot(path=str(OUT / 'dialog.png'))
    page.locator('#address-input').fill('取消的地址')
    page.locator('#cancel').click()
    assert page.locator('#replacement').is_hidden()
    page.locator('#edit-address').focus()
    page.keyboard.press('Enter')
    page.keyboard.press('Escape')
    assert not page.locator('#editor').is_visible()
    page.locator('#edit-address').click()
    page.locator('#address-input').fill('一\n二\n三\n四')
    page.locator('#confirm').click()
    assert page.locator('#error').inner_text()
    page.locator('#address-input').fill('长' * 80)
    page.locator('#confirm').click()
    assert '太长' in page.locator('#error').inner_text()
    page.locator('#address-input').fill('上海市浦东新区\n新地址 100 号')
    page.locator('#confirm').click()
    page.wait_for_function("!document.getElementById('editor').open")
    assert page.locator('#replacement span').all_text_contents() == ['上海市浦东新区', '新地址 100 号', '']
    panel.screenshot(path=str(OUT / 'edited.png'))
    with Image.open(OUT / 'initial.png') as before, Image.open(OUT / 'edited.png') as after:
        delta = ImageChops.difference(before.convert('RGB'), after.convert('RGB'))
        box = delta.getbbox()
        assert box and box[0] >= 126 and box[1] >= 1800 and box[2] <= 1064 and box[3] <= 2046, box
        delta.save(OUT / 'difference.png')
    with page.expect_download() as pending:
        page.locator('#save-json').click()
    pending.value.save_as(OUT / 'edited.json')
    data = json.loads((OUT / 'edited.json').read_text())
    assert data == {'merchant': '多联科技', 'phone': '18925023056', 'lines': ['上海市浦东新区', '新地址 100 号', '']}
    with page.expect_download() as pending:
        page.locator('#save').click()
    pending.value.save_as(OUT / 'edited.html')
    page.goto((OUT / 'edited.html').as_uri())
    page.evaluate('document.fonts.ready')
    assert page.locator('#replacement span').first.inner_text() == '上海市浦东新区'
    page.locator('#edit-address').click()
    assert page.locator('#address-input').input_value() == '上海市浦东新区\n新地址 100 号'
    page.locator('#address-input').fill('<img src=x onerror=alert(1)>')
    page.locator('#confirm').click()
    page.wait_for_function("!document.getElementById('editor').open")
    assert page.locator('#replacement img').count() == 0
    # Mobile: identical canvas, horizontal scrolling, dialog remains usable.
    page.set_viewport_size({'width': 390, 'height': 844})
    page.locator('#edit-address').click()
    bounds = page.locator('#editor').bounding_box()
    assert bounds['width'] <= 390
    assert not errors, errors
    assert not requests, requests
    browser.close()
