"""Generate a self-contained screenshot page with an address-only dialog."""
import argparse
import base64
import html
import json
import io
import shutil
from pathlib import Path

from PIL import Image
from address_to_html import ROOT


def export_page(config, output_dir):
    data = json.loads(Path(config).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get('merchant') != '多联科技' or data.get('phone') != '18925023056':
        raise ValueError('此页面只修改地址，商家和电话必须保持原样。')
    lines = data.get('lines')
    if (not isinstance(lines, list) or not 1 <= len(lines) <= 3
            or any(not isinstance(line, str) or '\n' in line or '\r' in line for line in lines)
            or not any(line.strip() for line in lines)):
        raise ValueError('lines 必须是一至三行地址，不能全部为空。')
    data = {"merchant": data['merchant'], "phone": data['phone'],
            "lines": lines + [''] * (3 - len(lines))}
    target = Path(output_dir)
    if target.exists():
        raise ValueError('输出目录已经存在，请换一个目录，避免覆盖。')
    source = ROOT / '2026-10-06 11.08.30.jpg'
    with Image.open(source) as image:
        if image.size != (1182, 2560):
            raise ValueError('此模板只适用于仓库中的 1182 × 2560 样例截图。')
        decoded = io.BytesIO()
        image.convert('RGB').save(decoded, format='PNG')
    photo = base64.b64encode(decoded.getvalue()).decode('ascii')
    font = base64.b64encode((ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf').read_bytes()).decode('ascii')
    # Escape JSON for an HTML script element, including malicious closing tags.
    state = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (ROOT / 'templates/full-page.html').read_text(encoding='utf-8')
    replacements = {'PHOTO': photo, 'FONT': font, 'STATE': state,
                    'SCRIPT': (ROOT / 'templates/full-page.js').read_text(encoding='utf-8'),
                    'LICENSE': html.escape((ROOT / 'assets/fonts/OFL.txt').read_text(encoding='utf-8'))}
    # A single pass prevents user data from being interpreted as placeholders.
    import re
    page = re.sub(r'@@(PHOTO|FONT|STATE|SCRIPT|LICENSE)@@',
                  lambda match: replacements[match.group(1)], template)
    target.mkdir(parents=True)
    (target / 'return-page.html').write_text(page, encoding='utf-8')
    (target / 'address.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'templates/full-page.js', target / 'full-page.js')
    shutil.copyfile(ROOT / 'docs/address-dialog.svg', target / 'address-dialog.svg')
    shutil.copyfile(ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf', target / 'NotoSansCJKsc-Regular.otf')
    shutil.copyfile(ROOT / 'assets/fonts/OFL.txt', target / 'OFL.txt')
    return target / 'return-page.html'


def main():
    parser = argparse.ArgumentParser(description='生成整张退货截图的离线地址弹窗网页。')
    parser.add_argument('--config', type=Path, default=ROOT / 'address.json')
    parser.add_argument('--output-dir', type=Path, default=Path('offline-return-page'))
    args = parser.parse_args()
    try:
        print(export_page(args.config, args.output_dir))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'生成失败：{exc}\n')


if __name__ == '__main__':
    main()
