"""CI/CD file analyzer — parses pipeline definitions from YAML, Dockerfile, Jenkinsfile."""

import re

import yaml

from app.analyzers.base import CodeAnalyzer
from app.models.domain import CodeEntity, Relationship
from app.utils.determinism import generate_entity_id

# File path patterns that indicate CI/CD configuration
_CICD_PATH_PATTERNS = [
    re.compile(r"\.github/workflows/.*\.ya?ml$"),
    re.compile(r"\.gitlab-ci\.ya?ml$"),
    re.compile(r"\.circleci/config\.ya?ml$"),
    re.compile(r"(^|/)docker-compose\.ya?ml$"),
]

_CICD_FILENAMES = {"Dockerfile", "Jenkinsfile"}


def _is_cicd_file(file_path: str) -> bool:
    """Check whether file_path matches a known CI/CD pattern."""
    for pattern in _CICD_PATH_PATTERNS:
        if pattern.search(file_path):
            return True
    # Exact filename match (basename)
    basename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
    return basename in _CICD_FILENAMES


class CICDFileAnalyzer(CodeAnalyzer):
    """Parses CI/CD configuration files into pipeline entities and relationships."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".yml", ".yaml"]

    @property
    def supported_filenames(self) -> list[str]:
        return ["Dockerfile", "Jenkinsfile"]

    def analyze_file(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        if not _is_cicd_file(file_path):
            return [], []

        basename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path

        if basename == "Dockerfile":
            return self._parse_dockerfile(file_path, content)
        if basename == "Jenkinsfile":
            return self._parse_jenkinsfile(file_path, content)
        if ".github/workflows" in file_path:
            return self._parse_github_actions(file_path, content)
        if ".gitlab-ci" in file_path:
            return self._parse_gitlab_ci(file_path, content)
        if ".circleci" in file_path:
            return self._parse_circleci(file_path, content)
        if "docker-compose" in basename:
            return self._parse_docker_compose(file_path, content)

        return [], []

    # ------------------------------------------------------------------
    # GitHub Actions
    # ------------------------------------------------------------------

    def _parse_github_actions(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return [], []
        if not isinstance(data, dict):
            return [], []

        # Triggers
        on_section = data.get("on") or data.get(True)  # YAML parses 'on' as True
        if isinstance(on_section, dict):
            for trigger_name in on_section:
                tid = generate_entity_id(file_path, f"trigger::{trigger_name}")
                entities.append(CodeEntity(
                    id=tid, name=str(trigger_name), entity_type="pipeline_trigger",
                    file_path=file_path, line_number=1,
                ))
        elif isinstance(on_section, list):
            for trigger_name in on_section:
                tid = generate_entity_id(file_path, f"trigger::{trigger_name}")
                entities.append(CodeEntity(
                    id=tid, name=str(trigger_name), entity_type="pipeline_trigger",
                    file_path=file_path, line_number=1,
                ))
        elif isinstance(on_section, str):
            tid = generate_entity_id(file_path, f"trigger::{on_section}")
            entities.append(CodeEntity(
                id=tid, name=on_section, entity_type="pipeline_trigger",
                file_path=file_path, line_number=1,
            ))

        # Jobs
        jobs = data.get("jobs", {})
        if not isinstance(jobs, dict):
            return entities, relationships

        job_ids: dict[str, str] = {}
        for job_name, job_def in jobs.items():
            jid = generate_entity_id(file_path, f"job::{job_name}")
            job_ids[job_name] = jid
            entities.append(CodeEntity(
                id=jid, name=job_name, entity_type="pipeline_job",
                file_path=file_path, line_number=1,
                metadata={"runs_on": job_def.get("runs-on", "") if isinstance(job_def, dict) else ""},
            ))

        # Dependencies (needs)
        for job_name, job_def in jobs.items():
            if not isinstance(job_def, dict):
                continue
            needs = job_def.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            for dep in needs:
                if dep in job_ids:
                    relationships.append(Relationship(
                        source_id=job_ids[job_name],
                        target_id=job_ids[dep],
                        relationship_type="depends_on",
                    ))

        # Trigger -> first jobs
        trigger_entities = [e for e in entities if e.entity_type == "pipeline_trigger"]
        jobs_without_deps = [
            jid for jname, jid in job_ids.items()
            if not any(r.source_id == jid and r.relationship_type == "depends_on" for r in relationships)
        ]
        for trigger in trigger_entities:
            for jid in jobs_without_deps:
                relationships.append(Relationship(
                    source_id=trigger.id,
                    target_id=jid,
                    relationship_type="triggers",
                ))

        return entities, relationships

    # ------------------------------------------------------------------
    # GitLab CI
    # ------------------------------------------------------------------

    def _parse_gitlab_ci(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return [], []
        if not isinstance(data, dict):
            return [], []

        # Stages
        stages = data.get("stages", [])
        stage_ids: dict[str, str] = {}
        for stage_name in stages:
            sid = generate_entity_id(file_path, f"stage::{stage_name}")
            stage_ids[stage_name] = sid
            entities.append(CodeEntity(
                id=sid, name=stage_name, entity_type="pipeline_stage",
                file_path=file_path, line_number=1,
            ))

        # Stage ordering
        for i in range(1, len(stages)):
            relationships.append(Relationship(
                source_id=stage_ids[stages[i - 1]],
                target_id=stage_ids[stages[i]],
                relationship_type="triggers",
            ))

        # Jobs
        reserved_keys = {"stages", "variables", "image", "services", "before_script",
                         "after_script", "cache", "include", "default", "workflow"}
        for job_name, job_def in data.items():
            if job_name.startswith(".") or job_name in reserved_keys:
                continue
            if not isinstance(job_def, dict):
                continue

            jid = generate_entity_id(file_path, f"job::{job_name}")
            stage = job_def.get("stage", "test")
            entities.append(CodeEntity(
                id=jid, name=job_name, entity_type="pipeline_job",
                file_path=file_path, line_number=1,
                metadata={"stage": stage},
            ))

            if stage in stage_ids:
                relationships.append(Relationship(
                    source_id=stage_ids[stage],
                    target_id=jid,
                    relationship_type="contains",
                ))

            # Dependencies
            deps = job_def.get("dependencies", []) or job_def.get("needs", [])
            if isinstance(deps, list):
                for dep in deps:
                    dep_name = dep if isinstance(dep, str) else dep.get("job", "") if isinstance(dep, dict) else ""
                    if dep_name:
                        dep_id = generate_entity_id(file_path, f"job::{dep_name}")
                        relationships.append(Relationship(
                            source_id=jid,
                            target_id=dep_id,
                            relationship_type="depends_on",
                        ))

        return entities, relationships

    # ------------------------------------------------------------------
    # CircleCI
    # ------------------------------------------------------------------

    def _parse_circleci(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return [], []
        if not isinstance(data, dict):
            return [], []

        # Jobs
        job_ids: dict[str, str] = {}
        for job_name in data.get("jobs", {}):
            jid = generate_entity_id(file_path, f"job::{job_name}")
            job_ids[job_name] = jid
            entities.append(CodeEntity(
                id=jid, name=job_name, entity_type="pipeline_job",
                file_path=file_path, line_number=1,
            ))

        # Workflows
        workflows = data.get("workflows", {})
        if isinstance(workflows, dict):
            for wf_name, wf_def in workflows.items():
                if wf_name == "version" or not isinstance(wf_def, dict):
                    continue
                wf_jobs = wf_def.get("jobs", [])
                for item in wf_jobs:
                    if isinstance(item, str):
                        continue
                    if isinstance(item, dict):
                        for jname, jconfig in item.items():
                            if isinstance(jconfig, dict) and "requires" in jconfig:
                                for req in jconfig["requires"]:
                                    if req in job_ids and jname in job_ids:
                                        relationships.append(Relationship(
                                            source_id=job_ids[jname],
                                            target_id=job_ids[req],
                                            relationship_type="depends_on",
                                        ))

        return entities, relationships

    # ------------------------------------------------------------------
    # Dockerfile
    # ------------------------------------------------------------------

    def _parse_dockerfile(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        stage_pattern = re.compile(r"^FROM\s+\S+\s+AS\s+(\S+)", re.IGNORECASE | re.MULTILINE)
        prev_id: str | None = None
        for i, match in enumerate(stage_pattern.finditer(content)):
            stage_name = match.group(1)
            sid = generate_entity_id(file_path, f"stage::{stage_name}")
            lineno = content[:match.start()].count("\n") + 1
            entities.append(CodeEntity(
                id=sid, name=stage_name, entity_type="pipeline_stage",
                file_path=file_path, line_number=lineno,
            ))
            if prev_id:
                relationships.append(Relationship(
                    source_id=prev_id, target_id=sid, relationship_type="triggers",
                ))
            prev_id = sid

        # If no multi-stage build, create a single stage
        if not entities:
            sid = generate_entity_id(file_path, "stage::build")
            entities.append(CodeEntity(
                id=sid, name="build", entity_type="pipeline_stage",
                file_path=file_path, line_number=1,
            ))

        return entities, relationships

    # ------------------------------------------------------------------
    # Jenkinsfile
    # ------------------------------------------------------------------

    def _parse_jenkinsfile(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        stage_pattern = re.compile(r"""stage\s*\(\s*['"]([^'"]+)['"]\s*\)""")
        prev_id: str | None = None
        for match in stage_pattern.finditer(content):
            stage_name = match.group(1)
            sid = generate_entity_id(file_path, f"stage::{stage_name}")
            lineno = content[:match.start()].count("\n") + 1
            entities.append(CodeEntity(
                id=sid, name=stage_name, entity_type="pipeline_stage",
                file_path=file_path, line_number=lineno,
            ))
            if prev_id:
                relationships.append(Relationship(
                    source_id=prev_id, target_id=sid, relationship_type="triggers",
                ))
            prev_id = sid

        return entities, relationships

    # ------------------------------------------------------------------
    # docker-compose
    # ------------------------------------------------------------------

    def _parse_docker_compose(
        self, file_path: str, content: str
    ) -> tuple[list[CodeEntity], list[Relationship]]:
        entities: list[CodeEntity] = []
        relationships: list[Relationship] = []

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            return [], []
        if not isinstance(data, dict):
            return [], []

        services = data.get("services", {})
        if not isinstance(services, dict):
            return [], []

        svc_ids: dict[str, str] = {}
        for svc_name in services:
            sid = generate_entity_id(file_path, f"service::{svc_name}")
            svc_ids[svc_name] = sid
            entities.append(CodeEntity(
                id=sid, name=svc_name, entity_type="pipeline_job",
                file_path=file_path, line_number=1,
                metadata={"kind": "docker-compose-service"},
            ))

        for svc_name, svc_def in services.items():
            if not isinstance(svc_def, dict):
                continue
            depends = svc_def.get("depends_on", [])
            if isinstance(depends, dict):
                depends = list(depends.keys())
            elif isinstance(depends, str):
                depends = [depends]
            for dep in depends:
                if dep in svc_ids:
                    relationships.append(Relationship(
                        source_id=svc_ids[svc_name],
                        target_id=svc_ids[dep],
                        relationship_type="depends_on",
                    ))

        return entities, relationships
