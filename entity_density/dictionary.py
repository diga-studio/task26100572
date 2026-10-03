"""Entity dictionary preparation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .normalization import normalize_text


@dataclass(frozen=True)
class Entity:
    """A single entity with a stable ID and its normalized aliases."""

    entity_id: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class EntityDictionary:
    """Prepared, reusable dictionary of entities."""

    entities: tuple[Entity, ...] = field(default_factory=tuple)


def prepare_dictionary(entities: Iterable[Mapping[str, object]]) -> EntityDictionary:
    """Build a reusable dictionary from entity definitions.

    Each definition must provide a stable ``id`` and a non-empty list of
    non-empty ``aliases``. Aliases are normalized with
    :func:`entity_density.normalize_text`; after normalization they must
    be unique across different entities (duplicates within one entity
    are collapsed).
    """
    prepared: list[Entity] = []
    seen_ids: set[str] = set()
    alias_owner: dict[str, str] = {}

    for definition in entities:
        entity_id = definition.get("id")
        if not isinstance(entity_id, str) or not entity_id:
            raise ValueError("each entity needs a non-empty string id")
        if entity_id in seen_ids:
            raise ValueError(f"duplicate entity id: {entity_id!r}")
        seen_ids.add(entity_id)

        raw_aliases = definition.get("aliases")
        if not isinstance(raw_aliases, Iterable) or isinstance(raw_aliases, (str, bytes)):
            raise ValueError(f"entity {entity_id!r} needs an iterable of aliases")

        normalized_aliases: list[str] = []
        for raw_alias in raw_aliases:
            if not isinstance(raw_alias, str):
                raise ValueError(f"entity {entity_id!r} has a non-string alias")
            alias = normalize_text(raw_alias)
            if not alias.strip(" "):
                raise ValueError(f"entity {entity_id!r} has an empty alias")
            owner = alias_owner.get(alias)
            if owner is not None and owner != entity_id:
                raise ValueError(
                    f"alias {alias!r} is shared by entities {owner!r} and {entity_id!r}"
                )
            if owner is None:
                alias_owner[alias] = entity_id
                normalized_aliases.append(alias)

        if not normalized_aliases:
            raise ValueError(f"entity {entity_id!r} needs at least one alias")
        prepared.append(Entity(entity_id=entity_id, aliases=tuple(normalized_aliases)))

    return EntityDictionary(entities=tuple(prepared))
