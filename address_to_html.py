"""Compatibility entry point; implementation lives in src/sf_return/."""
import sys
from pathlib import Path

# Keep source-tree commands usable without installing or building a package.
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from sf_return.render.address_panel import ROOT, export_address, load_address, main


if __name__ == '__main__':
    main()
