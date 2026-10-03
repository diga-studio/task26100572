"""In-memory entity dictionary."""

from __future__ import annotations

from types import MappingProxyType

from entity_density.normalize import normalize


class EntityDictionary:
    """Holds entities with stable IDs and their aliases.

    Normalized aliases are unique across entities.
    """

    def __init__(self) -> None:
        self._aliases: dict[str, str] = {}
        self._entities: dict[str, frozenset[str]] = {}

    def add_entity(self, entity_id: str, aliases: list[str]) -> None:
        """Register an entity with a stable ID and non-empty aliases."""
        if not isinstance(entity_id, str) or not entity_id:
            raise ValueError("entity_id must be a non-empty string")
        if entity_id in self._entities:
            raise ValueError(f"duplicate entity_id: {entity_id!r}")
        if not aliases:
            raise ValueError("aliases must be a non-empty list")
        normalized: list[str] = []
        for alias in aliases:
            if not isinstance(alias, str) or not alias:
                raise ValueError("aliases must be non-empty strings")
            norm = normalize(alias)
            if not norm.strip():
                raise ValueError(f"alias normalizes to empty: {alias!r}")
            owner = self._aliases.get(norm)
            if owner is not None and owner != entity_id:
                raise ValueError(
                    f"alias {alias!r} already belongs to entity {owner!r}"
                )
            normalized.append(norm)
        for norm in normalized:
            self._aliases[norm] = entity_id
        self._entities[entity_id] = frozenset(normalized)

    @property
    def aliases(self) -> dict[str, str]:
        """Mapping of normalized alias -> entity ID."""
        return MappingProxyType(self._aliases)
