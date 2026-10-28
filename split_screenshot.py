"""Compatibility entry point; implementation lives in src/sf_return/."""
import sys
from pathlib import Path

# Keep source-tree commands usable without installing or building a package.
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from sf_return.images.split import find_gray_panel, main, split_screenshot


if __name__ == '__main__':
    main()
