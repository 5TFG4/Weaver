"""
Strategy Metadata

Dataclasses for strategy plugin metadata.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StrategyMeta:
    """
    Metadata for a strategy plugin.

    Extracted from STRATEGY_META constant in strategy files
    without importing the module.
    """

    id: str
    class_name: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    # Internal: path to the module file
    module_path: Path | None = None

    def __post_init__(self) -> None:
        """Set name to id if not provided."""
        if not self.name:
            object.__setattr__(self, "name", self.id)

    @classmethod
    def from_dict(cls, data: dict, module_path: Path | None = None) -> "StrategyMeta":
        """
        Create StrategyMeta from a dictionary.

        Args:
            data: Dictionary with strategy metadata (from STRATEGY_META constant)
            module_path: Path to the module file

        Returns:
            StrategyMeta instance
        """
        return cls(
            id=data.get("id", ""),
            class_name=data.get("class", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            dependencies=data.get("dependencies", []),
            module_path=module_path,
        )
