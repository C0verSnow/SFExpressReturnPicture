"""Remote CI only: verify contact edits and the actual downloaded full PNG."""
import io
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageCms
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'offline-return-page'
BOXES = {'merchant': (362, 1708, 566, 1784), 'phone': (566, 1708, 946, 1784),
         'lines': (126, 1800, 1064, 2046)}


def changes_only(before, after, keys):
    with Image.open(before) as first, Image.open(after) as second:
        assert second.size == (1182, 2560)
        assert second.format == 'PNG'
        delta = ImageChops.difference(first.convert('RGB'), second.convert('RGB'))
        assert delta.getbbox(), 'Expected edited pixels'
        for key in keys:
            assert delta.crop(BOXES[key]).getbbox(), f'{key} was not rendered'
            delta.paste((0, 0, 0), BOXES[key])
        assert delta.getbbox() is None, 'Pixels outside edited text regions changed'


def confirm(page, path):
    with page.expect_download() as pending:
        page.locator('#confirm').click()
    assert pending.value.suggested_filename == 'return-page-edited.png'
    pending.value.save_as(path)
    page.wait_for_function("!document.getElementById('editor').open")


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
    context.set_offline(True)
    page = context.new_page()
    errors, requests, downloads = [], [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('download', lambda download: downloads.append(download))
    page.on('request', lambda request: requests.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    page.goto((OUT / 'return-page.html').as_uri())
    page.evaluate('document.fonts.ready')
    assert page.evaluate("document.fonts.check('48px Address', '新地址')")
    panel = page.locator('#page')
    assert panel.bounding_box() == {'x': 0, 'y': 0, 'width': 1182, 'height': 2560}
    panel.screenshot(path=str(OUT / 'initial.png'))
    with Image.open(ROOT / '2026-10-06 11.08.30.jpg') as source, Image.open(OUT / 'initial.png') as rendered:
        reference = source.convert('RGB')
        if source.info.get('icc_profile'):
            reference = ImageCms.profileToProfile(reference, ImageCms.ImageCmsProfile(io.BytesIO(source.info['icc_profile'])),
                                                   ImageCms.createProfile('sRGB'), outputMode='RGB')
        delta = ImageChops.difference(reference, rendered.convert('RGB'))
        delta.save(OUT / 'initial-difference.png')
        assert delta.getbbox() is None, (delta.getbbox(), delta.getextrema(), rendered.size)
    page.locator('#edit-address').click()
    assert page.locator('#merchant-input').input_value() == '多联科技'
    assert page.locator('#phone-input').input_value() == '18925023056'
    page.screenshot(path=str(OUT / 'dialog.png'))
    page.locator('#merchant-input').fill('取消名字')
    page.locator('#phone-input').fill('13800138000')
    page.locator('#address-input').fill('取消的地址')
    page.locator('#cancel').click()
    assert page.locator('#rendered-photo').is_hidden()
    page.locator('#edit-address').focus()
    page.keyboard.press('Enter')
    assert page.locator('#merchant-input').input_value() == '多联科技'
    page.keyboard.press('Escape')
    assert not page.locator('#editor').is_visible()
    assert not downloads
    page.locator('#edit-address').click()
    for selector, text in [('#merchant-input', '名' * 20), ('#phone-input', '1' * 40),
                           ('#address-input', '一\n二\n三\n四'), ('#address-input', '长' * 80)]:
        old = page.locator(selector).input_value()
        page.locator(selector).fill(text)
        page.locator('#confirm').click()
        page.wait_for_function("document.getElementById('error').textContent.length > 0")
        assert page.locator('#editor').is_visible()
        assert not downloads
        page.locator(selector).fill(old)
    page.locator('#merchant-input').fill('')
    page.locator('#confirm').click()
    assert page.locator('#editor').is_visible()
    assert not downloads
    page.locator('#merchant-input').fill('新商家')
    # Encoding failure leaves the previous state untouched and allows retry.
    page.evaluate('''() => {
      window.realToBlob = HTMLCanvasElement.prototype.toBlob;
      HTMLCanvasElement.prototype.toBlob = function(callback) { callback(null); };
    }''')
    page.locator('#confirm').click()
    page.wait_for_function("document.getElementById('error').textContent.includes('未能保存')")
    assert page.locator('#rendered-photo').is_hidden()
    assert not downloads
    assert json.loads(page.locator('#address-state').text_content())['merchant'] == '多联科技'
    page.evaluate('() => { HTMLCanvasElement.prototype.toBlob = window.realToBlob; }')
    confirm(page, OUT / 'merchant-only.png')
    changes_only(OUT / 'initial.png', OUT / 'merchant-only.png', ['merchant'])
    page.locator('#edit-address').click()
    page.locator('#phone-input').fill('13800138000')
    confirm(page, OUT / 'phone-edited.png')
    changes_only(OUT / 'merchant-only.png', OUT / 'phone-edited.png', ['phone'])
    page.locator('#edit-address').click()
    page.locator('#address-input').fill('上海市浦东新区\n新地址 100 号')
    confirm(page, OUT / 'confirmed-photo.png')
    changes_only(OUT / 'phone-edited.png', OUT / 'confirmed-photo.png', ['lines'])
    changes_only(OUT / 'initial.png', OUT / 'confirmed-photo.png', list(BOXES))
    panel.screenshot(path=str(OUT / 'edited.png'))
    with Image.open(OUT / 'confirmed-photo.png') as downloaded, Image.open(OUT / 'edited.png') as preview:
        assert ImageChops.difference(downloaded.convert('RGB'), preview.convert('RGB')).getbbox() is None
    with page.expect_download() as pending:
        page.locator('#save-json').click()
    pending.value.save_as(OUT / 'edited.json')
    data = json.loads((OUT / 'edited.json').read_text())
    assert data == {'merchant': '新商家', 'phone': '13800138000', 'lines': ['上海市浦东新区', '新地址 100 号', '']}
    with page.expect_download() as pending:
        page.locator('#save').click()
    pending.value.save_as(OUT / 'edited.html')
    page.goto((OUT / 'edited.html').as_uri())
    page.wait_for_function("!document.getElementById('rendered-photo').hidden")
    panel.screenshot(path=str(OUT / 'reopened.png'))
    with Image.open(OUT / 'confirmed-photo.png') as downloaded, Image.open(OUT / 'reopened.png') as reopened:
        delta = ImageChops.difference(downloaded.convert('RGB'), reopened.convert('RGB'))
        delta.save(OUT / 'reopened-difference.png')
        assert delta.getbbox() is None, (delta.getbbox(), delta.getextrema())
    with page.expect_download() as pending:
        page.locator('#save-photo').click()
    pending.value.save_as(OUT / 'saved-again.png')
    assert (OUT / 'saved-again.png').read_bytes() == (OUT / 'confirmed-photo.png').read_bytes()
    page.locator('#edit-address').click()
    assert page.locator('#merchant-input').input_value() == '新商家'
    assert page.locator('#phone-input').input_value() == '13800138000'
    assert page.locator('#address-input').input_value() == '上海市浦东新区\n新地址 100 号'
    # All data uses text/canvas, never HTML. Exported configuration is reusable.
    page.locator('#address-input').fill('</script><img src=x>')
    confirm(page, OUT / 'escaped-photo.png')
    assert page.locator('#page img:not(#persisted-photo)').count() == 1
    with page.expect_download() as pending:
        page.locator('#save-json').click()
    pending.value.save_as(OUT / 'escaped.json')
    regenerated = OUT / 'regenerated'
    subprocess.run([sys.executable, str(ROOT / 'full_page_to_html.py'), '--config', str(OUT / 'escaped.json'),
                    '--output-dir', str(regenerated)], check=True)
    page.goto((regenerated / 'return-page.html').as_uri())
    page.wait_for_function("!document.getElementById('rendered-photo').hidden")
    assert page.locator('#page img:not(#persisted-photo)').count() == 1
    page.locator('#edit-address').click()
    assert page.locator('#merchant-input').input_value() == '新商家'
    assert page.locator('#address-input').input_value() == '</script><img src=x>'
    # Restoring original values restores every original pixel in the downloaded PNG.
    page.locator('#merchant-input').fill('多联科技')
    page.locator('#phone-input').fill('18925023056')
    original = json.loads((ROOT / 'address.json').read_text())
    page.locator('#address-input').fill('\n'.join(original['lines']))
    confirm(page, OUT / 'restored.png')
    with Image.open(OUT / 'initial.png') as initial, Image.open(OUT / 'restored.png') as restored:
        assert ImageChops.difference(initial.convert('RGB'), restored.convert('RGB')).getbbox() is None
    assert page.locator('#rendered-photo').is_hidden()
    # Mobile dialog and download work at a different viewport and device scale.
    mobile = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    mobile.set_offline(True)
    mobile_page = mobile.new_page()
    mobile_page.goto((OUT / 'return-page.html').as_uri())
    mobile_page.locator('#edit-address').click()
    bounds = mobile_page.locator('#editor').bounding_box()
    assert bounds['width'] <= 390 and bounds['height'] <= 812
    mobile_page.locator('#merchant-input').fill('新商家')
    mobile_page.locator('#phone-input').fill('13800138000')
    mobile_page.locator('#address-input').fill('上海市浦东新区\n新地址 100 号')
    confirm(mobile_page, OUT / 'mobile-photo.png')
    assert (OUT / 'mobile-photo.png').read_bytes() == (OUT / 'confirmed-photo.png').read_bytes()
    assert not errors, errors
    assert not requests, requests
    browser.close()
