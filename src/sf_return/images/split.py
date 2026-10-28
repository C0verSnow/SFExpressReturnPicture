"""Split a saved screenshot above, inside, and below an address panel."""

import argparse
from pathlib import Path

from PIL import Image, ImageOps


def find_gray_panel(image):
    """Find broad light-gray rows, allowing text and JPEG compression noise."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    step = max(1, width // 400)
    xs = range(width // 20, width - width // 20, step)
    pixels = rgb.load()
    gray_rows = []
    for y in range(height):
        count = sum(
            230 <= min(pixels[x, y]) and max(pixels[x, y]) <= 250
            and max(pixels[x, y]) - min(pixels[x, y]) <= 8
            for x in xs
        )
        if count >= len(xs) * 0.55:
            gray_rows.append(y)
    if not gray_rows:
        raise ValueError("没有找到灰色区块，请用 --top 和 --bottom 指定上下边界。")

    gap = max(2, round(height * 0.012))
    groups = []
    start = previous = gray_rows[0]
    for y in gray_rows[1:]:
        if y - previous > gap:
            groups.append((start, previous + 1))
            start = y
        previous = y
    groups.append((start, previous + 1))
    minimum = max(20, round(height * 0.02))
    candidates = [(top, bottom) for top, bottom in groups
                  if bottom - top >= minimum and 0 < top < bottom < height]
    if len(candidates) != 1:
        raise ValueError(
            f"找到 {len(candidates)} 个可能的灰色区块 {candidates}，"
            "请用 --top 和 --bottom 指定商家地址区块的上下边界。"
        )
    return candidates[0]


def split_screenshot(source, output_dir, top=None, bottom=None):
    if (top is None) != (bottom is None):
        raise ValueError("--top 和 --bottom 必须一起填写。")
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    width, height = image.size
    if top is None:
        top, bottom = find_gray_panel(image)
    if not 0 < top < bottom < height:
        raise ValueError(f"边界必须满足 0 < top < bottom < 图片高度（{height}）。")

    output_dir = Path(output_dir)
    paths = [output_dir / name for name in
             ("01_top.png", "02_address.png", "03_bottom.png")]
    if any(path.exists() for path in paths):
        raise ValueError("输出图片已经存在，请换一个输出目录，避免覆盖。")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, (start, end) in zip(paths, ((0, top), (top, bottom), (bottom, height))):
        image.crop((0, start, width, end)).save(path, "PNG")
    return paths, (top, bottom)


def main():
    parser = argparse.ArgumentParser(description="把长截图按商家地址灰色区块切成三张 PNG。")
    parser.add_argument("image", type=Path, help="已保存的长截图路径")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--top", type=int, help="灰色区第一行的像素坐标，从 0 开始")
    parser.add_argument("--bottom", type=int, help="灰色区结束后的第一行像素坐标")
    args = parser.parse_args()
    try:
        paths, (top, bottom) = split_screenshot(
            args.image, args.output_dir, args.top, args.bottom
        )
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        parser.exit(1, f"切图失败：{exc}\n")
    print(f"灰色区边界：top={top}, bottom={bottom}")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
