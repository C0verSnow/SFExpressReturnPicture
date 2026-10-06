"""Run only in remote CI: file:// rendering, editing, downloads and visual checks."""
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "offline-address"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    context = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
    page = context.new_page()
    errors, remote_requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: remote_requests.append(request.url)
            if request.url.startswith(("http:", "https:")) else None)
    context.set_offline(True)
    page.goto((OUTPUT / "address.html").as_uri())
    page.evaluate("document.fonts.ready")
    assert page.evaluate("document.fonts.check('48px Address', '商家地址')")
    assert page.locator('[contenteditable]').count() == 5
    assert page.locator('#panel').bounding_box() == {
        "x": 0, "y": 0, "width": 1182, "height": 469}
    page.locator('#panel').screenshot(path=str(OUTPUT / "rendered.png"))
    # Compare canvas, background and text placement with the supplied crop.
    with Image.open(ROOT / "output/02_address.png") as reference, Image.open(OUTPUT / "rendered.png") as rendered:
        assert rendered.size == reference.size
        delta = ImageChops.difference(reference.convert('RGB'), rendered.convert('RGB'))
        mae = sum(ImageStat.Stat(delta).mean) / 3
        assert mae < 15, f"Address reconstruction drifted: MAE={mae}"
        comparison = Image.new('RGB', (1182, 469 * 2))
        comparison.paste(reference, (0, 0))
        comparison.paste(rendered, (0, 469))
        comparison.save(OUTPUT / "comparison.png")
        delta.save(OUTPUT / "difference.png")
        (OUTPUT / 'visual-metrics.json').write_text(json.dumps({'mean_absolute_error': mae}, indent=2))
    page.locator('#merchant').fill('测试商家')
    page.locator('#phone').fill('13800138000')
    page.locator('#line0').fill('广东省广州市 新地址')
    with page.expect_download() as pending:
        page.locator('#save-json').click()
    pending.value.save_as(OUTPUT / 'edited.json')
    data = json.loads((OUTPUT / 'edited.json').read_text())
    assert data['merchant'] == '测试商家'
    assert data['phone'] == '13800138000'
    assert data['lines'][0] == '广东省广州市 新地址'
    with page.expect_download() as pending:
        page.locator('#save').click()
    pending.value.save_as(OUTPUT / 'edited.html')
    page.goto((OUTPUT / 'edited.html').as_uri())
    page.evaluate('document.fonts.ready')
    assert page.locator('#merchant').inner_text() == '测试商家'
    assert page.locator('#phone').inner_text() == '13800138000'
    assert page.evaluate("document.fonts.check('48px Address', '新地址')")
    page.locator('#merchant').fill('再次编辑')
    with page.expect_download() as pending:
        page.locator('#save-json').click()
    pending.value.save_as(OUTPUT / 'edited-again.json')
    assert json.loads((OUTPUT / 'edited-again.json').read_text())['merchant'] == '再次编辑'
    page.goto((OUTPUT / 'address.svg').as_uri())
    page.evaluate('document.fonts.ready')
    assert page.locator('text').count() == 7
    assert page.evaluate("document.fonts.check('48px Address', '商家地址')")
    page.locator('svg').screenshot(path=str(OUTPUT / 'svg-rendered.png'))
    assert not errors, errors
    assert not remote_requests, remote_requests
    browser.close()
