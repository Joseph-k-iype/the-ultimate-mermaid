"""Tests for component detector."""

import pytest

from app.analyzers.component_detector import detect_components
from app.models.domain import CodeEntity


def _entity(eid: str, name: str, fp: str, etype: str = "function") -> CodeEntity:
    return CodeEntity(id=eid, name=name, entity_type=etype, file_path=fp, line_number=1)


def test_basic_grouping():
    entities = [
        _entity("1", "login", "auth/login.py"),
        _entity("2", "register", "auth/register.py"),
        _entity("3", "hash_pw", "auth/utils.py"),
        _entity("4", "get_user", "users/service.py"),
        _entity("5", "list_users", "users/views.py"),
        _entity("6", "User", "users/models.py"),
    ]
    result = detect_components(entities)

    assert "auth" in result
    assert "users" in result
    assert len(result["auth"]) == 3
    assert len(result["users"]) == 3

    # Check metadata injection
    assert entities[0].metadata["component"] == "auth"
    assert entities[3].metadata["component"] == "users"


def test_src_prefix_uses_second_level():
    entities = [
        _entity("1", "a", "src/auth/login.py"),
        _entity("2", "b", "src/auth/register.py"),
        _entity("3", "c", "src/auth/utils.py"),
        _entity("4", "d", "src/users/service.py"),
        _entity("5", "e", "src/users/views.py"),
        _entity("6", "f", "src/users/models.py"),
    ]
    result = detect_components(entities)

    assert "auth" in result
    assert "users" in result


def test_small_components_merged():
    entities = [
        _entity("1", "a", "auth/login.py"),
        _entity("2", "b", "auth/register.py"),
        _entity("3", "c", "auth/utils.py"),
        _entity("4", "d", "config/settings.py"),  # only 1 entity
    ]
    result = detect_components(entities)

    assert "auth" in result
    # config should be merged into "other"
    assert "other" in result
    assert "4" in result["other"]


def test_empty_input():
    result = detect_components([])
    assert result == {}


def test_single_file():
    entities = [_entity("1", "main", "main.py")]
    result = detect_components(entities)
    assert len(result) >= 1


def test_root_level_files():
    entities = [
        _entity("1", "a", "main.py"),
        _entity("2", "b", "config.py"),
        _entity("3", "c", "utils.py"),
    ]
    result = detect_components(entities)
    assert "root" in result
    assert len(result["root"]) == 3
