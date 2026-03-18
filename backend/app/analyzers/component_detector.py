"""Component detection — groups entities by logical component based on directory structure."""

import os
from collections import defaultdict

from app.models.domain import CodeEntity

# Files that indicate a package/component boundary
_PACKAGE_MARKERS = {"__init__.py", "package.json", "go.mod", "Cargo.toml", "pom.xml"}

_MIN_COMPONENT_SIZE = 3
_MAX_COMPONENT_SIZE = 80


def detect_components(entities: list[CodeEntity]) -> dict[str, list[str]]:
    """Group entities by detected logical component.

    Returns {component_name: [entity_id, ...]}.
    Also injects ``metadata["component"]`` into each entity.
    """
    if not entities:
        return {}

    # Extract unique directory paths
    dir_entities: dict[str, list[CodeEntity]] = defaultdict(list)
    for entity in entities:
        parts = entity.file_path.split("/")
        if len(parts) > 1:
            dir_entities["/".join(parts[:-1])].append(entity)
        else:
            dir_entities["root"].append(entity)

    # Determine grouping level
    # If top-level is a common source dir (src, lib, app), use second level
    top_dirs = set()
    for d in dir_entities:
        parts = d.split("/")
        if parts:
            top_dirs.add(parts[0])

    common_src_dirs = {"src", "lib", "app", "pkg", "internal", "cmd"}
    use_second_level = len(top_dirs) == 1 and top_dirs.pop() in common_src_dirs

    # Group entities by component
    raw_groups: dict[str, list[CodeEntity]] = defaultdict(list)
    for entity in entities:
        parts = entity.file_path.split("/")
        if len(parts) <= 1:
            component = "root"
        elif use_second_level and len(parts) > 2:
            component = parts[1]
        elif use_second_level and len(parts) == 2:
            component = parts[1].rsplit(".", 1)[0]  # strip extension for files at src level
        else:
            component = parts[0]
        raw_groups[component].append(entity)

    # Merge small components
    result: dict[str, list[CodeEntity]] = {}
    small: list[CodeEntity] = []
    for name, group in raw_groups.items():
        if len(group) < _MIN_COMPONENT_SIZE:
            small.extend(group)
        else:
            result[name] = group

    if small:
        if result:
            result["other"] = small
        else:
            # Everything is small — just use original groups
            result = dict(raw_groups)

    # Split large components by looking one level deeper
    final: dict[str, list[CodeEntity]] = {}
    for name, group in result.items():
        if len(group) > _MAX_COMPONENT_SIZE:
            sub_groups: dict[str, list[CodeEntity]] = defaultdict(list)
            for entity in group:
                parts = entity.file_path.split("/")
                depth = 2 if use_second_level else 1
                if len(parts) > depth + 1:
                    sub_name = f"{name}/{parts[depth]}"
                else:
                    sub_name = name
                sub_groups[sub_name].append(entity)
            final.update(sub_groups)
        else:
            final[name] = group

    # Inject metadata and build return dict
    component_map: dict[str, list[str]] = {}
    for component_name, group in final.items():
        entity_ids = []
        for entity in group:
            entity.metadata["component"] = component_name
            entity_ids.append(entity.id)
        component_map[component_name] = entity_ids

    return component_map
