"""Chef pipeline: a fridge photo in, a ranked recipe report out.

Import order matters slightly: .env has to be loaded before tools.py builds
its Tavily client, so the load happens here at package import time.
"""

from dotenv import load_dotenv

load_dotenv()

from .config import DEFAULT_IMAGE_DIR, REPORT_PATH  # noqa: E402
from .images import resolve_images  # noqa: E402
from .ranking import rank, ratio  # noqa: E402
from .report import render  # noqa: E402
from .stages import brainstorm, fetch_recipe, score, see_fridge  # noqa: E402

__all__ = [
    "DEFAULT_IMAGE_DIR",
    "REPORT_PATH",
    "resolve_images",
    "see_fridge",
    "brainstorm",
    "fetch_recipe",
    "score",
    "rank",
    "ratio",
    "render",
]
