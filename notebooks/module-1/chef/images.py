"""Finding and encoding the fridge photos.

Separated from the stages because "which files am I looking at" is a
different job from "what food is in them", and this half can be tested
without touching an API.
"""

import base64
from pathlib import Path

from .config import DEFAULT_IMAGE_DIR, MAX_IMAGES, MIME_TYPES


def encode_image(image_path: Path) -> tuple[str, str]:
    """Read one image file as base64 plus its mime type."""
    suffix = image_path.suffix.lower()
    if suffix not in MIME_TYPES:
        raise ValueError(
            f"Unsupported image type '{suffix}' for {image_path.name}. "
            f"Use one of: {', '.join(sorted(MIME_TYPES))}"
        )
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return encoded, MIME_TYPES[suffix]


def resolve_images(paths: list[Path] | None = None) -> list[Path]:
    """Work out which image files to send, from whatever the caller gave.

    Accepts any mix of files and directories. A directory contributes every
    supported image inside it. With nothing passed, falls back to the
    default resources directory.

    Results are sorted so a run is reproducible, and capped at MAX_IMAGES so
    a directory of holiday photos cannot quietly cost a fortune.
    """
    if not paths:
        paths = [DEFAULT_IMAGE_DIR]

    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            # Sorted inside each directory so fridge-1, fridge-2, fridge-3
            # arrive in the order you named them.
            found += sorted(
                child
                for child in path.iterdir()
                if child.suffix.lower() in MIME_TYPES
            )
        elif path.exists():
            found.append(path)
        else:
            raise FileNotFoundError(f"No such image or directory: {path}")

    # Dedupe while preserving order, in case a file was named twice or sat
    # inside a directory that was also passed.
    unique = list(dict.fromkeys(found))

    if not unique:
        raise FileNotFoundError(
            f"No supported images found in: {', '.join(str(p) for p in paths)}"
        )

    return unique[:MAX_IMAGES]
