"""Generate a self-contained screenshot page with a contact editor and PNG export."""
import argparse
import base64
import json
import io
import shutil
from pathlib import Path

from PIL import Image, ImageCms
from ..paths import ADDRESS, DEFAULT_CONFIG, FONTS, REGIONS, ROOT, SOURCE_IMAGE, TEMPLATES


def export_page(config, output_dir):
    data = json.loads(Path(config).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError('地址配置必须是 JSON 对象。')
    for key in ('merchant', 'phone'):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or '\n' in value or '\r' in value:
            raise ValueError(f'{key} 必须是单行非空文字。')
    lines = data.get('lines')
    if (not isinstance(lines, list) or len(lines) != 3
            or any(not isinstance(line, str) or not line.strip() or '\n' in line or '\r' in line for line in lines)
            or not any(line.strip() for line in lines)):
        raise ValueError('lines 必须是三行非空地址。')
    data = {"merchant": data['merchant'].strip(), "phone": data['phone'].strip(),
            "lines": [line.strip() for line in lines]}
    target = Path(output_dir)
    if target.exists():
        raise ValueError('输出目录已经存在，请换一个目录，避免覆盖。')
    source = SOURCE_IMAGE
    with Image.open(source) as image:
        if image.size != (1182, 2560):
            raise ValueError('此模板只适用于仓库中的 1182 × 2560 样例截图。')
        decoded = io.BytesIO()
        rgb = image.convert('RGB')
        if image.info.get('icc_profile'):
            rgb = ImageCms.profileToProfile(rgb, ImageCms.ImageCmsProfile(io.BytesIO(image.info['icc_profile'])),
                                           ImageCms.createProfile('sRGB'), outputMode='RGB')
        rgb.info.clear()
        rgb.save(decoded, format='PNG')
    photo = base64.b64encode(decoded.getvalue()).decode('ascii')
    font = base64.b64encode((FONTS / 'NotoSansCJKsc-Regular.otf').read_bytes()).decode('ascii')
    # Escape JSON for an HTML script element, including malicious closing tags.
    state = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (TEMPLATES / 'full-page.html').read_text(encoding='utf-8')
    regions = (REGIONS / 'list.json').read_text(encoding='utf-8')
    # Ship the pure parser and browser editor together: one inline script also works offline.
    script = ((ADDRESS / 'contact.js').read_text(encoding='utf-8') + '\n'
              + (TEMPLATES / 'full-page.js').read_text(encoding='utf-8'))
    replacements = {'PHOTO': photo, 'FONT': font, 'STATE': state, 'REGIONS': regions,
                    'REGION_LICENSE': (REGIONS / 'LICENSE').read_text(encoding='utf-8'),
                    'SCRIPT': script}
    # A single pass prevents user data from being interpreted as placeholders.
    import re
    page = re.sub(r'@@(PHOTO|FONT|STATE|SCRIPT|REGIONS|REGION_LICENSE)@@',
                  lambda match: replacements[match.group(1)], template)
    target.mkdir(parents=True)
    (target / 'return-page.html').write_text(page, encoding='utf-8')
    (target / 'address.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (target / 'full-page.js').write_text(script, encoding='utf-8')
    shutil.copyfile(ROOT / 'docs/address-dialog.svg', target / 'address-dialog.svg')
    shutil.copyfile(FONTS / 'NotoSansCJKsc-Regular.otf', target / 'NotoSansCJKsc-Regular.otf')
    shutil.copyfile(FONTS / 'OFL.txt', target / 'OFL.txt')
    shutil.copyfile(REGIONS / 'LICENSE', target / 'regions-LICENSE.txt')
    return target / 'return-page.html'


def main():
    parser = argparse.ArgumentParser(description='生成可修改名字、电话和地址并保存照片的离线网页。')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--output-dir', type=Path, default=Path('offline-return-page'))
    args = parser.parse_args()
    try:
        print(export_page(args.config, args.output_dir))
    except (OSError, ValueError) as exc:
        parser.exit(1, f'生成失败：{exc}\n')


if __name__ == '__main__':
    main()
