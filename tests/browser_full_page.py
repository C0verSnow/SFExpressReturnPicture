"""Remote CI: actual PNG pixels, field boundaries, validation and responsive UI."""
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageCms
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'offline-return-page'
BOXES = {'merchant': (362, 1708, 566, 1784), 'phone': (566, 1708, 946, 1784),
         'lines': (126, 1800, 1064, 2046)}
DEFAULT = json.loads((ROOT / 'address.json').read_text())
ORIGINAL = json.loads((ROOT / 'tests/original-address.json').read_text())


def pixels(page, name):
    data = page.locator('#rendered-photo').evaluate("canvas => canvas.toDataURL('image/png').split(',')[1]")
    path = OUT / name
    path.write_bytes(base64.b64decode(data))
    return path


def changes_only(before, after, keys):
    with Image.open(before) as first, Image.open(after) as second:
        assert second.size == (1182, 2560)
        assert second.format == 'PNG'
        delta = ImageChops.difference(first.convert('RGB'), second.convert('RGB'))
        assert delta.getbbox(), 'Expected edited pixels'
        for key in keys:
            assert delta.crop(BOXES[key]).getbbox(), f'{key} was not rendered'
            delta.paste((0, 0, 0), BOXES[key])
        assert delta.getbbox() is None, 'Pixels outside edited fields changed'


def confirm(page, path):
    with page.expect_download() as pending:
        page.locator('#confirm').click()
    pending.value.save_as(path)
    assert pending.value.suggested_filename == 'return-page-edited.png'
    page.wait_for_function("!document.getElementById('editor').open")


with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 900})
    context.set_offline(True)
    page = context.new_page()
    errors, requests, downloads = [], [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('download', lambda download: downloads.append(download))
    page.on('request', lambda request: requests.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    page.goto((OUT / 'return-page.html').as_uri())
    page.wait_for_function("!document.getElementById('edit-address').disabled")
    assert page.locator('#tools button').count() == 1
    assert page.locator('#license, #save, #save-json').count() == 0
    initial = pixels(page, 'initial.png')
    with Image.open(ROOT / '2026-10-06 11.08.30.jpg') as source:
        reference = ImageCms.profileToProfile(source.convert('RGB'),
            ImageCms.ImageCmsProfile(io.BytesIO(source.info['icc_profile'])),
            ImageCms.createProfile('sRGB'), outputMode='RGB') if source.info.get('icc_profile') else source.convert('RGB')
        reference.save(OUT / 'original.png')
    changes_only(OUT / 'original.png', initial, list(BOXES))
    page.locator('#edit-address').click()
    assert page.locator('#merchant-input').input_value() == '张三'
    assert page.locator('#phone-input').input_value() == '18888888888'
    assert page.locator('#address-input').input_value() == '广东省\n深圳市\n南山区人才公园'
    page.screenshot(path=str(OUT / 'dialog.png'))
    page.locator('#merchant-input').fill('取消名字')
    page.locator('#cancel').click()
    assert pixels(page, 'cancelled.png').read_bytes() == initial.read_bytes()
    page.locator('#edit-address').focus()
    page.keyboard.press('Enter')
    assert page.locator('#merchant-input').input_value() == '张三'
    page.keyboard.press('Escape')
    assert not page.locator('#editor').is_visible()
    assert not downloads
    page.locator('#edit-address').click()
    for selector, text in [('#merchant-input', '名' * 20), ('#phone-input', '1' * 40),
                           ('#address-input', '一\n二\n三\n四'), ('#address-input', '一\n二'),
                           ('#address-input', '一\n \n三'), ('#address-input', '长' * 80 + '\n二\n三')]:
        old = page.locator(selector).input_value()
        page.locator(selector).fill(text)
        page.locator('#confirm').click()
        page.wait_for_function("document.getElementById('error').textContent.length > 0")
        assert not downloads
        page.locator(selector).fill(old)
    page.locator('#merchant-input').fill('新商家')
    page.evaluate('''() => {
      window.realToBlob = HTMLCanvasElement.prototype.toBlob;
      HTMLCanvasElement.prototype.toBlob = function(callback) { callback(null); };
    }''')
    page.locator('#confirm').click()
    page.wait_for_function("document.getElementById('error').textContent.includes('未能保存')")
    assert json.loads(page.locator('#address-state').text_content()) == DEFAULT
    assert not downloads
    page.evaluate('() => { HTMLCanvasElement.prototype.toBlob = window.realToBlob; }')
    confirm(page, OUT / 'merchant-only.png')
    changes_only(initial, OUT / 'merchant-only.png', ['merchant'])
    page.locator('#edit-address').click()
    page.locator('#phone-input').fill('13800138000')
    confirm(page, OUT / 'phone-edited.png')
    changes_only(OUT / 'merchant-only.png', OUT / 'phone-edited.png', ['phone'])
    page.locator('#edit-address').click()
    page.locator('#address-input').fill('上海市\n浦东新区\n新地址 100 号')
    confirm(page, OUT / 'confirmed-photo.png')
    changes_only(OUT / 'phone-edited.png', OUT / 'confirmed-photo.png', ['lines'])
    with Image.open(OUT / 'confirmed-photo.png') as photo, Image.open(pixels(page, 'preview-pixels.png')) as preview:
        assert ImageChops.difference(photo.convert('RGB'), preview.convert('RGB')).getbbox() is None
    with page.expect_download() as pending:
        page.locator('#save-photo').click()
    pending.value.save_as(OUT / 'saved-again.png')
    assert (OUT / 'saved-again.png').read_bytes() == (OUT / 'confirmed-photo.png').read_bytes()
    page.locator('#edit-address').click()
    page.locator('#address-input').fill('</script><img src=x>\n第二行\n第三行')
    confirm(page, OUT / 'escaped-photo.png')
    assert page.locator('#page img').count() == 1
    for key in ('merchant', 'phone'):
        if not page.locator('#editor').is_visible():
            page.locator('#edit-address').click()
        page.locator('#' + key + '-input').fill(ORIGINAL[key])
    page.locator('#address-input').fill('\n'.join(ORIGINAL['lines']))
    confirm(page, OUT / 'restored.png')
    with Image.open(OUT / 'original.png') as original, Image.open(OUT / 'restored.png') as restored:
        assert ImageChops.difference(original, restored.convert('RGB')).getbbox() is None
    # Classify device hints, resize across categories, and inspect every recommended canvas.
    for platform, width, height, touch in [('desktop', 1920, 1080, False), ('laptop', 1440, 900, False),
                                         ('tablet', 768, 1024, True), ('mobile', 390, 844, True)]:
        device = browser.new_context(viewport={'width': width, 'height': height},
                                     has_touch=touch, is_mobile=touch, device_scale_factor=2 if touch else 1)
        device.set_offline(True)
        view = device.new_page()
        view.on('pageerror', lambda error: errors.append(str(error)))
        view.goto((OUT / 'return-page.html').as_uri())
        view.wait_for_function("!document.getElementById('save-photo').disabled")
        assert view.locator('html').get_attribute('data-platform') == platform
        assert view.locator('html').get_attribute('data-design-canvas') == f'{width}x{height}'
        assert view.evaluate('document.documentElement.scrollWidth <= innerWidth')
        bounds = view.locator('#page').bounding_box()
        assert abs(bounds['width'] / bounds['height'] - 1182 / 2560) < .001
        view.locator('#save-photo').scroll_into_view_if_needed()
        view.screenshot(path=str(OUT / f'{platform}.png'))
        view.locator('#edit-address').click()
        dialog = view.locator('#editor').bounding_box()
        assert dialog['x'] >= 0 and dialog['y'] >= 0
        assert dialog['width'] <= width and dialog['height'] <= height - 32
        view.locator('#merchant-input').fill('新商家')
        view.locator('#phone-input').fill('13800138000')
        view.locator('#address-input').fill('上海市\n浦东新区\n新地址 100 号')
        confirm(view, OUT / f'{platform}-photo.png')
        assert (OUT / f'{platform}-photo.png').read_bytes() == (OUT / 'confirmed-photo.png').read_bytes()
        if platform == 'desktop':
            view.set_viewport_size({'width': 390, 'height': 844})
            view.wait_for_function("document.documentElement.dataset.platform === 'mobile'")
            assert view.evaluate('document.documentElement.scrollWidth <= innerWidth')
        device.close()
    assert not errors, errors
    assert not requests, requests
    browser.close()
