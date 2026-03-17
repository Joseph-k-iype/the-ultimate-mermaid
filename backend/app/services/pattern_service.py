import re
from datetime import datetime, timezone

from app.models.pattern import (
    PatternCreateRequest,
    PatternListItem,
    PatternModel,
    PatternResponse,
    PatternSearchResponse,
    PatternStatus,
    PatternUpdateRequest,
)
from app.utils.determinism import generate_pattern_id

# Valid status transitions: current -> set of allowed next statuses
_VALID_TRANSITIONS: dict[PatternStatus, set[PatternStatus]] = {
    PatternStatus.draft: {PatternStatus.review},
    PatternStatus.review: {PatternStatus.approved, PatternStatus.draft},
    PatternStatus.approved: {PatternStatus.deprecated},
    PatternStatus.deprecated: {PatternStatus.draft},
}

_MERMAID_PATTERN = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)

SYSTEM_DESIGN_TEMPLATE = """---
title: "[Pattern Title]"
owner: "[Team/Author]"
status: draft
tags: []
---

# [Pattern Title]

## Overview
_Brief summary of what this pattern solves and when to use it._

## Context & Problem Statement
_What is the problem? What forces are at play?_

## Solution Architecture
```mermaid
graph TD
    A[Component A] --> B[Component B]
```
_Describe the high-level architecture._

## Components
| Component | Responsibility | Technology |
|-----------|---------------|------------|
| | | |

## Data Flow
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant DB
    Client->>API: Request
    API->>DB: Query
    DB-->>API: Result
    API-->>Client: Response
```

## API Contracts
_Key endpoints, message formats, or interface definitions._

## Decision Log
| Decision | Rationale | Date |
|----------|-----------|------|
| | | |

## Trade-offs
_What was sacrificed and why. Known limitations._

## References
_Links to related patterns, ADRs, or external resources._
"""


class PatternService:
    """In-memory pattern storage with search and status workflow."""

    def __init__(self) -> None:
        self._patterns: dict[str, PatternModel] = {}

    @staticmethod
    def _extract_mermaid_blocks(content: str) -> list[str]:
        return _MERMAID_PATTERN.findall(content)

    def _to_response(self, model: PatternModel) -> PatternResponse:
        return PatternResponse(**model.model_dump())

    def _to_list_item(self, model: PatternModel) -> PatternListItem:
        return PatternListItem(
            id=model.id,
            title=model.title,
            description=model.description,
            owner=model.owner,
            status=model.status,
            tags=model.tags,
            updated_at=model.updated_at,
            version=model.version,
        )

    def create(self, req: PatternCreateRequest) -> PatternResponse:
        pattern_id = generate_pattern_id(req.title, req.owner)
        now = datetime.now(timezone.utc)
        model = PatternModel(
            id=pattern_id,
            title=req.title,
            description=req.description,
            owner=req.owner,
            tags=req.tags,
            content=req.content,
            mermaid_diagrams=self._extract_mermaid_blocks(req.content),
            created_at=now,
            updated_at=now,
            linked_scan_id=req.linked_scan_id,
        )
        self._patterns[pattern_id] = model

        from app.graph import graph_service

        if graph_service.is_available:
            graph_service.store_pattern(model)

        return self._to_response(model)

    def get(self, pattern_id: str) -> PatternResponse | None:
        model = self._patterns.get(pattern_id)
        if model is None:
            return None
        return self._to_response(model)

    def update(self, pattern_id: str, req: PatternUpdateRequest) -> PatternResponse | None:
        model = self._patterns.get(pattern_id)
        if model is None:
            return None

        updates = req.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(model, key, value)

        if "content" in updates:
            model.mermaid_diagrams = self._extract_mermaid_blocks(model.content)

        model.version += 1
        model.updated_at = datetime.now(timezone.utc)

        from app.graph import graph_service

        if graph_service.is_available:
            graph_updates = req.model_dump(exclude_unset=True)
            graph_updates["version"] = model.version
            graph_service.update_pattern(model.id, graph_updates)

        return self._to_response(model)

    def delete(self, pattern_id: str) -> bool:
        removed = self._patterns.pop(pattern_id, None) is not None

        if removed:
            from app.graph import graph_service

            if graph_service.is_available:
                graph_service.delete_pattern(pattern_id)

        return removed

    def search(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        status: PatternStatus | None = None,
        owner: str | None = None,
    ) -> PatternSearchResponse:
        # Try graph-powered search for SKOS-enriched results
        from app.graph import graph_service

        if graph_service.is_available:
            graph_results = graph_service.search_patterns(query, tags, status, owner)
            if graph_results is not None:
                items = [
                    PatternListItem(
                        id=r["id"],
                        title=r["title"],
                        description=r["description"] or "",
                        owner=r["owner"] or "",
                        status=PatternStatus(r["status"]),
                        tags=[],  # Graph doesn't return tags in search
                        updated_at=datetime.now(timezone.utc),
                        version=r["version"] or 1,
                    )
                    for r in graph_results
                ]
                return PatternSearchResponse(results=items, total=len(items))

        # Fallback to in-memory search
        results = list(self._patterns.values())

        if query:
            q = query.lower()
            results = [
                p for p in results
                if q in p.title.lower()
                or q in p.description.lower()
                or q in p.content.lower()
            ]

        if tags:
            tag_set = set(tags)
            results = [p for p in results if tag_set & set(p.tags)]

        if status is not None:
            results = [p for p in results if p.status == status]

        if owner:
            results = [p for p in results if p.owner == owner]

        items = [self._to_list_item(p) for p in results]
        return PatternSearchResponse(results=items, total=len(items))

    def transition_status(
        self, pattern_id: str, new_status: PatternStatus
    ) -> PatternResponse | None:
        model = self._patterns.get(pattern_id)
        if model is None:
            return None

        allowed = _VALID_TRANSITIONS.get(model.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{model.status.value}' to '{new_status.value}'. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        model.status = new_status
        model.updated_at = datetime.now(timezone.utc)
        model.version += 1
        return self._to_response(model)

    def find_related(self, pattern_id: str) -> list[PatternListItem]:
        """Find related patterns via graph. Returns [] if graph unavailable."""
        from app.graph import graph_service

        if not graph_service.is_available:
            return []

        related = graph_service.find_related_patterns(pattern_id)
        return [
            PatternListItem(
                id=r["id"],
                title=r["title"],
                description=r["description"] or "",
                owner=r["owner"] or "",
                status=PatternStatus(r["status"]),
                tags=[],
                updated_at=datetime.now(timezone.utc),
                version=r["version"] or 1,
            )
            for r in related
        ]

    def get_system_design_template(self) -> str:
        return SYSTEM_DESIGN_TEMPLATE


pattern_service = PatternService()
