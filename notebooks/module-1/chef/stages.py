"""The four stages that involve a model.

Each function takes plain Python in and returns plain Python out, so any one
of them can be run on its own in a notebook cell to check its behaviour
before the next is wired up.
"""

from pathlib import Path

from langchain.messages import HumanMessage

from .config import MAX_RECIPES, PANTRY_STAPLES
from .images import encode_image
from .runner import ask
from .schemas import Coverage, Fridge, Recipe, RecipeIdeas
from .tools import web_search


def see_fridge(image_paths: list[Path]) -> list[str]:
    """Stage 1: read every food item out of one or more fridge photos.

    All the photos go into a single message. That matters: one call means
    the model sees every shelf at once and can recognise that the same
    carton photographed twice is one carton. Calling it per photo and
    merging the lists afterwards would double-count everything in the
    overlap, and no amount of prompting downstream would fix it.
    """
    # A multimodal message is a list of content blocks rather than a string.
    # `content_blocks=` is the type-safe initializer; it populates `content`
    # underneath, so the older `content=[...]` form behaves identically.
    # Blocks are ordered, so the label lands before the image it describes.
    blocks: list[dict] = [
        {
            "type": "text",
            "text": (
                f"Here are {len(image_paths)} photo(s) of one fridge. "
                "List every food item you can see across all of them."
            ),
        }
    ]
    for number, image_path in enumerate(image_paths, 1):
        img_b64, mime = encode_image(image_path)
        blocks.append({"type": "text", "text": f"Photo {number}: {image_path.name}"})
        blocks.append({"type": "image", "base64": img_b64, "mime_type": mime})

    fridge = ask(
        Fridge,
        "You are a meticulous kitchen assistant. Identify every distinct food "
        "item visible in the photos. Use plain names such as 'eggs' or "
        "'cheddar cheese'. Do not guess at items you cannot actually see. "
        "The photos are different angles or shelves of the SAME fridge and "
        "may overlap, so list each item once no matter how many photos it "
        "appears in.",
        messages=[HumanMessage(content_blocks=blocks)],
    )

    # Belt and braces on the dedupe instruction above: fold exact
    # case-insensitive repeats, keeping the model's original spelling and
    # ordering. Near-misses like "milk" and "whole milk" still get through,
    # which is the model's job to avoid.
    seen: dict[str, str] = {}
    for item in fridge.items:
        seen.setdefault(item.strip().lower(), item.strip())
    return list(seen.values())


def brainstorm(items: list[str]) -> list[str]:
    """Stage 2: propose dish names that suit the available ingredients."""
    # Deliberately no web search here. Naming plausible dishes is something
    # the model already knows how to do, and searching this early would
    # anchor the whole pipeline on whatever the first result happened to be.
    ideas = ask(
        RecipeIdeas,
        f"You are a professional chef. Propose exactly {MAX_RECIPES} well-known "
        "dishes that could realistically be cooked from the ingredients given. "
        "Return dish names only. Favour dishes that use several of the "
        "ingredients rather than just one.",
        messages=[HumanMessage(content=f"Ingredients on hand: {', '.join(items)}")],
    )
    # Trim in case the model is generous with its "exactly".
    return ideas.names[:MAX_RECIPES]


def fetch_recipe(name: str) -> Recipe:
    """Stage 3: search the web for a real recipe and extract it."""
    # The only stage with a tool. The model searches, reads the results, and
    # may search again before answering, which is the agent loop from 1.2.
    return ask(
        Recipe,
        "You are a recipe researcher. Use the web_search tool to find a real, "
        "published recipe for the dish the user names. Extract its full "
        "ingredient list with quantities, its ordered steps, and the URL you "
        "took it from. Never invent a recipe or a URL.\n\n"
        # Without this the model tries to restrict itself to trusted recipe
        # sites and sends a query of nothing but operators, which the search
        # API rejects outright. Telling it to describe the dish in words is
        # the fix; the search engine finds the recipe sites on its own.
        "Search using plain descriptive terms, for example "
        "'palak paneer recipe ingredients'. Never use search operators such "
        "as site:, filetype: or quotes. Every query must contain the dish "
        "name as ordinary words.",
        messages=[HumanMessage(content=f"Find a recipe for: {name}")],
        tools=[web_search],
    )


def score(items: list[str], recipe: Recipe) -> Coverage:
    """Stage 4: judge which recipe ingredients the fridge covers.

    The model does this rather than Python set arithmetic, because a recipe
    says "2 large eggs, beaten" where the fridge says "eggs". Exact string
    matching would call that missing and rank every recipe wrongly.
    """
    return ask(
        Coverage,
        "You compare a recipe against a fridge. Match on the underlying "
        "ingredient, ignoring quantities and preparation: '2 large eggs, "
        "beaten' is covered by 'eggs'. Treat these as always available and "
        f"leave them out of both lists entirely: {', '.join(PANTRY_STAPLES)}. "
        "Every remaining recipe ingredient must appear in exactly one list.",
        messages=[
            HumanMessage(
                content=(
                    f"Fridge: {', '.join(items)}\n\n"
                    f"Recipe '{recipe.name}' needs: {', '.join(recipe.ingredients)}"
                )
            )
        ],
    )
