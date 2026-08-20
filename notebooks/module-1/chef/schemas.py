"""Pydantic schemas that shape each stage's output.

These are the contract between stages. Passing one of these classes as
`response_format=` to `create_agent` forces the model to return an instance
of it instead of free text, which is what lets the pipeline pass data from
one stage to the next without any parsing.

Field descriptions are not decoration: they are sent to the model as part of
the schema, so they are the cheapest place to correct a misbehaving stage.
"""

from pydantic import BaseModel, Field


class Fridge(BaseModel):
    """Stage 1 output: what the camera can actually see."""

    items: list[str] = Field(
        description="Ingredient names only, no quantities or packaging"
    )


class RecipeIdeas(BaseModel):
    """Stage 2 output: dish names to research, nothing more."""

    names: list[str] = Field(
        description="Dish names only, with no ingredients or instructions"
    )


class Recipe(BaseModel):
    """Stage 3 output: a real recipe lifted from a real page."""

    name: str
    ingredients: list[str] = Field(
        description="One ingredient per entry, including its quantity"
    )
    steps: list[str] = Field(description="Cooking steps in order")
    source_url: str = Field(description="URL the recipe was taken from")


class Coverage(BaseModel):
    """Stage 4 output: the fridge judged against one recipe.

    Splitting into two lists rather than returning a score keeps the
    judgement with the model and the arithmetic in Python, where it can be
    printed and checked.
    """

    have: list[str] = Field(description="Recipe ingredients the fridge covers")
    missing: list[str] = Field(description="Recipe ingredients the fridge lacks")
