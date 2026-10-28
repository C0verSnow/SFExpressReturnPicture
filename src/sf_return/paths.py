"""Resolve source resources from this checkout, independent of the working directory."""
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
TEMPLATES = PACKAGE / 'render' / 'templates'
ADDRESS = PACKAGE / 'address'
REGIONS = ADDRESS / 'data'
FONTS = ROOT / 'assets' / 'fonts'
SOURCE_IMAGE = ROOT / '2026-10-06 11.08.30.jpg'
DEFAULT_CONFIG = ROOT / 'address.json'
