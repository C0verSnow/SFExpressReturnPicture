"""Remote regression: issue #9 addresses and dark/automatic-dark photo pixels."""
import base64
import io
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'pages-check'


def image_bytes(page):
    return base64.b64decode(page.locator('#rendered-photo').evaluate(
        "canvas => canvas.toDataURL('image/png').split(',')[1]"))


def same_pixels(first, second):
    with Image.open(io.BytesIO(first)) as a, Image.open(io.BytesIO(second)) as b:
        return ImageChops.difference(a.convert('RGB'), b.convert('RGB')).getbbox() is None


def check_addresses(page):
    cases = [
        ('北京 北京市 通州区 宋庄镇 北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院',
         '北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院'),
        ('广东省广东省深圳市深圳市南山区南山区科技园1号', '广东省深圳市南山区科技园1号'),
        ('广东省深圳市南山区粤海街道广东省深圳市南山区粤海街道科技园1号',
         '广东省深圳市南山区粤海街道科技园1号'),
        ('北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院',
         '北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院'),
        ('北京市朝阳区北京市朝阳区实验学校1号楼', '北京市朝阳区实验学校1号楼'),
        ('广东省深圳市南山区南山大道北京银行1号', '广东省深圳市南山区南山大道北京银行1号'),
        ('广东省深圳市南山区科技园（东门）1号', '广东省深圳市南山区科技园（东门）1号'),
        ('北京通州区1号', '北京市通州区1号'),
        ('广东省深圳市南山区广东省深圳市南山区广东省深圳市南山区科技园1号',
         '广东省深圳市南山区科技园1号'),
        ('广东省深圳市南山区粤海街道粤海街道科技园1号',
         '广东省深圳市南山区粤海街道科技园1号'),
        ('福建省泉州市惠安县 张坂镇台商投资区中熙产业园3期2栋C梯5楼-1(拼多多平台Coldelement旗舰店）',
         '福建省泉州市惠安县张坂镇台商投资区中熙产业园3期2栋C梯5楼-1(拼多多平台Coldelement旗舰店）'),
    ]
    for address, expected in cases:
        page.locator('#paste-input').fill('收件人：张三 电话：13800138000 地址：' + address)
        assert page.locator('#error').text_content() == '', (address, page.locator('#error').text_content())
        lines = page.locator('#address-input').input_value().splitlines()
        assert len(lines) == 3 and all(lines), lines
        assert ''.join(lines) == expected, (address, lines, expected)
        assert '已省略' not in page.locator('#parse-status').text_content()
    base = '福建省泉州市惠安县张坂镇台商投资区中熙产业园3期2栋C梯5楼-1'
    # The literal issue sample fits; make the note longer to exercise actual overflow.
    for note in ('(' + '拼多多平台Coldelement旗舰店' * 10 + '）',
                 '（店铺(' + '平台说明' * 30 + '）备注)',
                 '（' + '平台说明' * 30 + '）(另一条说明)'):
        page.locator('#paste-input').fill('冷元素售后 18059175529 ' + base + note)
        assert page.locator('#error').text_content() == ''
        assert page.locator('#merchant-input').input_value() == '冷元素售后'
        assert page.locator('#phone-input').input_value() == '18059175529'
        assert ''.join(page.locator('#address-input').input_value().splitlines()) == base
        assert '已省略括号附注' in page.locator('#parse-status').text_content()
    # Drop only the rightmost note when that is enough; retain the useful short note.
    page.locator('#paste-input').fill('张三 13800138000 ' + base + '（东门）(' + '说明' * 100 + ')')
    assert ''.join(page.locator('#address-input').input_value().splitlines()) == base + '（东门）'
    assert '已省略括号附注' in page.locator('#parse-status').text_content()
    previous = [page.locator(s).input_value() for s in
                ('#merchant-input', '#phone-input', '#address-input')]
    for address in (base + '(' + '说明' * 100, base + '长' * 100 + '(店铺说明)',
                    base + '长' * 100 + ')'):
        page.locator('#paste-input').fill('李四 13900139000 ' + address)
        assert page.locator('#error').text_content()
        assert [page.locator(s).input_value() for s in
                ('#merchant-input', '#phone-input', '#address-input')] == previous


def assert_readable_editor(page):
    # The photo keeps its original palette; the surrounding form must also be readable.
    for selector in ('#editor', '#paste-input', '#merchant-input', '#phone-input', '#address-input'):
        colors = page.locator(selector).evaluate('''element => {
          const style = getComputedStyle(element);
          return [style.color, style.backgroundColor];
        }''')
        assert colors == ['rgb(37, 40, 50)', 'rgb(255, 255, 255)' if selector == '#editor'
                          else 'rgb(250, 251, 252)'], (selector, colors)


def run():
    OUT.mkdir(exist_ok=True)
    failures = []
    with sync_playwright() as p:
        for filename in ('pages-site/index.html', 'offline-return-page/return-page.html'):
            initial = edited = visual = None
            for mode in ('light', 'dark', 'auto-dark'):
                # Isolate Chromium's process-wide text caches so the only changed
                # variable is the theme, not shaping work from previous scenarios.
                browser = p.chromium.launch()
                context = browser.new_context(viewport={'width': 390, 'height': 844},
                                              color_scheme='light' if mode == 'light' else 'dark')
                context.set_offline(True)
                page = context.new_page()
                if mode == 'auto-dark':
                    context.new_cdp_session(page).send('Emulation.setAutoDarkModeOverride', {'enabled': True})
                label = ('site' if filename.startswith('pages-site') else 'offline') + '-' + mode
                page.goto((ROOT / filename).as_uri())
                page.wait_for_function("!document.getElementById('save-photo').disabled")
                current = image_bytes(page)
                (OUT / f'issue9-{label}-initial.png').write_bytes(current)
                preview = page.locator('#rendered-photo').screenshot(
                    style='#tools,#edit-address{visibility:hidden}')
                (OUT / f'issue9-{label}-visible.png').write_bytes(preview)
                if mode == 'light':
                    initial, visual = current, preview
                else:
                    if not same_pixels(initial, current):
                        failures.append(f'{label}: initial PNG changes with dark mode')
                    if not same_pixels(visual, preview):
                        failures.append(f'{label}: visible photo changes with dark mode')
                page.locator('#edit-address').click()
                page.screenshot(path=str(OUT / f'issue9-{label}-dialog.png'))
                try:
                    assert_readable_editor(page)
                    check_addresses(page)
                except AssertionError as error:
                    failures.append(f'{label}: address regression: {error}')
                page.locator('#merchant-input').fill('新商家')
                page.locator('#phone-input').fill('13800138000')
                page.locator('#address-input').fill('福建省泉州市惠安县\n张坂镇台商投资区中熙产业园\n3期2栋C梯5楼-1')
                with page.expect_download() as pending:
                    page.locator('#confirm').click()
                target = OUT / f'issue9-{label}-edited.png'
                pending.value.save_as(target)
                page.wait_for_function("!document.getElementById('editor').open")
                exported = target.read_bytes()
                if not same_pixels(exported, image_bytes(page)):
                    failures.append(f'{label}: download differs from preview')
                if mode == 'light':
                    edited = exported
                elif not same_pixels(edited, exported):
                    failures.append(f'{label}: edited PNG changes with dark mode')
                # Force a second draw from the existing preview, the user's exact edit path.
                page.locator('#edit-address').click()
                page.locator('#merchant-input').fill('张三')
                with page.expect_download() as pending:
                    page.locator('#confirm').click()
                pending.value.save_as(OUT / f'issue9-{label}-second-edit.png')
                page.wait_for_function("!document.getElementById('editor').open")
                second = (OUT / f'issue9-{label}-second-edit.png').read_bytes()
                with Image.open(io.BytesIO(exported)) as a, Image.open(io.BytesIO(second)) as b:
                    delta = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
                    delta.paste((0, 0, 0), (362, 1708, 566, 1784))
                    if delta.getbbox() is not None:
                        failures.append(f'{label}: second edit changed unedited photo pixels')
                context.close()
                browser.close()
    assert not failures, '\n'.join(failures)


if __name__ == '__main__':
    run()
