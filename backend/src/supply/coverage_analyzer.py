from __future__ import annotations

from src.shared.utils import compute_coverage_score


def calculate_coverage_score(capabilities: list[str], equipment: list[str], specialists: list[str]) -> float:
    """
    Calculate a simple coverage score based on counts of capabilities, equipment, and specialists.
    """
    return compute_coverage_score(capabilities, equipment, specialists)
