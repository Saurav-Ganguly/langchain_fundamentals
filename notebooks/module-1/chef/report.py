"""Rendering the ranked results as markdown.

Kept apart from ranking so the presentation can change without touching the
scoring, and so this function can be tested with hand-built objects and no
API calls at all.
"""

from .ranking import Scored, ratio


def render(ranked: list[Scored], items: list[str]) -> str:
    """Format the winning recipe, with the runners-up in a table below."""
    winner, coverage = ranked[0]
    covered = len(coverage.have)
    total = covered + len(coverage.missing)

    lines = [
        f"# {winner.name}",
        "",
        f"**Ingredient coverage: {ratio(coverage):.0%}** ({covered} of {total})",
        "",
        # Angle brackets keep bare URLs clickable without a link label.
        f"Source: <{winner.source_url}>",
        "",
        "## From your fridge",
        "",
    ]
    lines += [f"- {item}" for item in coverage.have]

    # Only worth a heading if there is actually a shopping list.
    if coverage.missing:
        lines += ["", "## You still need", ""]
        lines += [f"- {item}" for item in coverage.missing]

    lines += ["", "## Ingredients", ""]
    lines += [f"- {item}" for item in winner.ingredients]

    lines += ["", "## Method", ""]
    lines += [f"{n}. {step}" for n, step in enumerate(winner.steps, 1)]

    # The runners-up exist so a rejected recipe can be reconsidered once you
    # see how little it was actually missing.
    if len(ranked) > 1:
        lines += [
            "",
            "## Also considered",
            "",
            "| Dish | Coverage | Missing |",
            "| --- | --- | --- |",
        ]
        for recipe, cov in ranked[1:]:
            missing = ", ".join(cov.missing) or "nothing"
            lines.append(f"| {recipe.name} | {ratio(cov):.0%} | {missing} |")

    lines += ["", "---", "", f"Spotted in your fridge: {', '.join(items)}", ""]
    return "\n".join(lines)
