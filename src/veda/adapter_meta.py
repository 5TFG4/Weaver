"""
Adapter Metadata

Dataclasses for adapter plugin metadata.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AdapterMeta:
    """
    Metadata for an adapter plugin.

    Extracted from ADAPTER_META constant in adapter files
    without importing the module.
    """

    id: str
    class_name: str
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    features: list[str] = field(default_factory=list)
    # Internal: path to the module file
    module_path: Path | None = None

    def __post_init__(self) -> None:
        """Set name to id if not provided."""
        if not self.name:
            object.__setattr__(self, "name", self.id)

    def supports_feature(self, feature: str) -> bool:
        """
        Check if adapter supports a specific feature.

        Args:
            feature: Feature name to check

        Returns:
            True if feature is supported, False otherwise
        """
        return feature in self.features

    @classmethod
    def from_dict(cls, data: dict, module_path: Path | None = None) -> "AdapterMeta":
        """
        Create AdapterMeta from a dictionary.

        Args:
            data: Dictionary with adapter metadata (from ADAPTER_META constant)
            module_path: Path to the module file

        Returns:
            AdapterMeta instance
        """
        return cls(
            id=data.get("id", ""),
            class_name=data.get("class", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            features=data.get("features", []),
            module_path=module_path,
        )
