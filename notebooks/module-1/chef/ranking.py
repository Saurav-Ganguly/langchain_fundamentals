"""Turning coverage judgements into an order.

No model here on purpose. Stage 4 already made the hard call about what
counts as covered, so ranking is arithmetic. A number you can print beats an
opinion you cannot inspect.
"""

from .schemas import Coverage, Recipe

# A scored candidate is the recipe paired with its coverage judgement.
Scored = tuple[Recipe, Coverage]


def ratio(coverage: Coverage) -> float:
    """Fraction of non-staple ingredients the fridge can supply.

    Returns 0.0 for an empty judgement, which sinks a recipe the coverage
    stage failed to evaluate rather than crashing the run.
    """
    total = len(coverage.have) + len(coverage.missing)
    return len(coverage.have) / total if total else 0.0


def rank(scored: list[Scored]) -> list[Scored]:
    """Best coverage first, fewer ingredients breaking ties.

    The tie-break favours the simpler dish: given two recipes you can fully
    cook tonight, the one with eight ingredients beats the one with twenty.
    """
    return sorted(scored, key=lambda pair: (-ratio(pair[1]), len(pair[0].ingredients)))
