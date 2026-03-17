import hashlib

from app.models.domain import CodeEntity, Relationship


def generate_entity_id(file_path: str, name: str) -> str:
    return f"{file_path}::{name}"


def generate_scan_id(url: str, branch: str) -> str:
    return hashlib.sha256(f"{url}:{branch}".encode()).hexdigest()


def generate_pattern_id(title: str, owner: str) -> str:
    return hashlib.sha256(f"{title}:{owner}".encode()).hexdigest()


def canonical_sort_entities(entities: list[CodeEntity]) -> list[CodeEntity]:
    return sorted(entities, key=lambda e: e.id)


def canonical_sort_relationships(relationships: list[Relationship]) -> list[Relationship]:
    return sorted(
        relationships,
        key=lambda r: (r.source_id, r.target_id, r.relationship_type),
    )
