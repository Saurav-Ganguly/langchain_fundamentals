"""Professional chef: turn fridge photos into a ranked recipe report.

This file is only the orchestration. Every step lives in the chef package,
so the whole pipeline reads top to bottom in one screen:

    see the fridge -> brainstorm dish names -> fetch real recipes
    -> score ingredient coverage -> rank -> write markdown

Usage:
    uv run python notebooks/module-1/my_chef.py                  # resources/fridge/
    uv run python notebooks/module-1/my_chef.py top.jpg door.jpg # named photos
    uv run python notebooks/module-1/my_chef.py ~/fridge-photos  # a directory

Several photos of one fridge are fine and encouraged: one per shelf reads
far better than a single wide shot. They are sent together in one request,
so an item photographed twice is still counted once.
"""

import sys
from pathlib import Path

from chef import (
    REPORT_PATH,
    brainstorm,
    fetch_recipe,
    rank,
    ratio,
    render,
    resolve_images,
    score,
    see_fridge,
)


def cook(image_paths: list[Path]) -> Path:
    """Run the full pipeline and write the report. Returns the report path."""
    # Stage 1. Everything downstream depends on this list being right, so it
    # is printed first and in full.
    print(f"Reading {len(image_paths)} photo(s): "
          f"{', '.join(p.name for p in image_paths)}")
    items = see_fridge(image_paths)
    if not items:
        sys.exit("No food found in those photos. Are they actually of a fridge?")
    print(f"Found {len(items)} items: {', '.join(items)}\n")

    # Stage 2. Names only, no research yet.
    names = brainstorm(items)
    print(f"Candidate dishes: {', '.join(names)}\n")

    # Stages 3 and 4, paired per dish. Fetching and scoring together means a
    # recipe is judged the moment it arrives, and the running output tells
    # you which dish a failure belongs to.
    # A dish that fails to research is skipped rather than fatal. Research
    # depends on live search results, so one bad query should not discard
    # the recipes already paid for and gathered.
    scored = []
    for name in names:
        try:
            recipe = fetch_recipe(name)
            coverage = score(items, recipe)
        except Exception as error:
            print(f"{name}: skipped ({type(error).__name__}: {error})")
            continue
        scored.append((recipe, coverage))
        print(f"{recipe.name}: {ratio(coverage):.0%} covered  {recipe.source_url}")

    if not scored:
        sys.exit("Could not research any of the candidate dishes.")

    # Stage 5. Pure functions from here, no further API calls.
    ranked = rank(scored)
    REPORT_PATH.write_text(render(ranked, items), encoding="utf-8")

    print(f"\nWinner: {ranked[0][0].name} at {ratio(ranked[0][1]):.0%} coverage")
    return REPORT_PATH


def main():
    # Any mix of files and directories. Nothing given means the default
    # resources/fridge/ folder.
    requested = [Path(arg) for arg in sys.argv[1:]]

    # Resolve up front so a bad path fails immediately, rather than during
    # base64 encoding where the traceback says nothing useful.
    try:
        image_paths = resolve_images(requested)
    except (FileNotFoundError, ValueError) as error:
        sys.exit(str(error))

    print(f"Report written to {cook(image_paths)}")


if __name__ == "__main__":
    main()
