import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import CodeEntity, Relationship


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_entities() -> list[CodeEntity]:
    return [
        CodeEntity(
            id="app.py::UserModel",
            name="UserModel",
            entity_type="class",
            file_path="app.py",
            line_number=1,
            metadata={"attributes": ["name", "email"], "methods": ["save"]},
        ),
        CodeEntity(
            id="app.py::OrderModel",
            name="OrderModel",
            entity_type="class",
            file_path="app.py",
            line_number=20,
            metadata={"attributes": ["total", "user_id"]},
        ),
        CodeEntity(
            id="app.py::get_users",
            name="get_users",
            entity_type="endpoint",
            file_path="app.py",
            line_number=40,
        ),
        CodeEntity(
            id="app.py::process_order",
            name="process_order",
            entity_type="function",
            file_path="app.py",
            line_number=50,
        ),
        CodeEntity(
            id="app.py::read_csv",
            name="read_csv",
            entity_type="file_reader",
            file_path="app.py",
            line_number=60,
        ),
        CodeEntity(
            id="app.py::write_db",
            name="write_db",
            entity_type="db_write",
            file_path="app.py",
            line_number=70,
        ),
    ]


@pytest.fixture
def sample_relationships() -> list[Relationship]:
    return [
        Relationship(
            source_id="app.py::OrderModel",
            target_id="app.py::UserModel",
            relationship_type="uses",
        ),
        Relationship(
            source_id="app.py::get_users",
            target_id="app.py::process_order",
            relationship_type="calls",
        ),
        Relationship(
            source_id="app.py::process_order",
            target_id="app.py::write_db",
            relationship_type="calls",
        ),
        Relationship(
            source_id="app.py::read_csv",
            target_id="app.py::process_order",
            relationship_type="calls",
        ),
    ]
