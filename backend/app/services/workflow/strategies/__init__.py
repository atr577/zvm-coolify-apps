"""Workflow strategies for different project types."""
from app.services.workflow.strategies.base import BaseStrategy
from app.services.workflow.strategies.discover import DiscoverStrategy
from app.services.workflow.strategies.remix import RemixStrategy

# Strategy instances (singleton pattern)
STRATEGIES = {
    'discover': DiscoverStrategy(),
    'remix': RemixStrategy(),
}


def get_strategy(project_type: str) -> BaseStrategy:
    """
    Get strategy for project type.

    Args:
        project_type: 'discover' or 'remix'

    Returns:
        Strategy instance for the project type
    """
    return STRATEGIES.get(project_type, DiscoverStrategy())


__all__ = [
    "BaseStrategy",
    "DiscoverStrategy",
    "RemixStrategy",
    "get_strategy",
]
