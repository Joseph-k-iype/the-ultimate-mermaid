"""Tests for CI/CD file analyzer."""

import pytest

from app.analyzers.cicd_analyzer import CICDFileAnalyzer


@pytest.fixture
def analyzer():
    return CICDFileAnalyzer()


class TestGitHubActions:
    def test_parse_basic_workflow(self, analyzer):
        content = """
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - run: echo build
"""
        entities, rels = analyzer.analyze_file(".github/workflows/ci.yml", content)

        # Should find triggers, jobs
        trigger_names = {e.name for e in entities if e.entity_type == "pipeline_trigger"}
        assert "push" in trigger_names
        assert "pull_request" in trigger_names

        job_names = {e.name for e in entities if e.entity_type == "pipeline_job"}
        assert "test" in job_names
        assert "build" in job_names

        # build depends_on test
        depends_rels = [r for r in rels if r.relationship_type == "depends_on"]
        assert len(depends_rels) >= 1

        # triggers from trigger -> jobs
        trigger_rels = [r for r in rels if r.relationship_type == "triggers"]
        assert len(trigger_rels) >= 1

    def test_non_cicd_yaml_ignored(self, analyzer):
        content = """
config:
  debug: true
  port: 8080
"""
        entities, rels = analyzer.analyze_file("config/settings.yml", content)
        assert entities == []
        assert rels == []

    def test_on_as_dict(self, analyzer):
        content = """
name: Deploy
on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
"""
        entities, rels = analyzer.analyze_file(".github/workflows/deploy.yml", content)
        trigger_names = {e.name for e in entities if e.entity_type == "pipeline_trigger"}
        assert "push" in trigger_names
        assert "schedule" in trigger_names


class TestGitLabCI:
    def test_parse_stages_and_jobs(self, analyzer):
        content = """
stages:
  - build
  - test
  - deploy

build_job:
  stage: build
  script: make build

test_job:
  stage: test
  script: make test
  needs:
    - build_job

deploy_job:
  stage: deploy
  script: make deploy
"""
        entities, rels = analyzer.analyze_file(".gitlab-ci.yml", content)

        stage_names = {e.name for e in entities if e.entity_type == "pipeline_stage"}
        assert {"build", "test", "deploy"} == stage_names

        job_names = {e.name for e in entities if e.entity_type == "pipeline_job"}
        assert "build_job" in job_names
        assert "test_job" in job_names

        # Stage ordering triggers
        trigger_rels = [r for r in rels if r.relationship_type == "triggers"]
        assert len(trigger_rels) >= 2

        # test_job depends_on build_job
        depends_rels = [r for r in rels if r.relationship_type == "depends_on"]
        assert len(depends_rels) >= 1


class TestDockerfile:
    def test_multistage_build(self, analyzer):
        content = """FROM node:18 AS builder
WORKDIR /app
RUN npm install

FROM nginx:alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
"""
        entities, rels = analyzer.analyze_file("Dockerfile", content)

        stage_names = {e.name for e in entities if e.entity_type == "pipeline_stage"}
        assert "builder" in stage_names
        assert "runtime" in stage_names

        # builder triggers runtime
        assert len(rels) >= 1

    def test_single_stage(self, analyzer):
        content = """FROM python:3.11
WORKDIR /app
CMD ["python", "main.py"]
"""
        entities, rels = analyzer.analyze_file("Dockerfile", content)
        assert len(entities) == 1
        assert entities[0].name == "build"


class TestJenkinsfile:
    def test_parse_stages(self, analyzer):
        content = """
pipeline {
    agent any
    stages {
        stage('Build') {
            steps { sh 'make build' }
        }
        stage('Test') {
            steps { sh 'make test' }
        }
        stage('Deploy') {
            steps { sh 'make deploy' }
        }
    }
}
"""
        entities, rels = analyzer.analyze_file("Jenkinsfile", content)
        names = {e.name for e in entities}
        assert {"Build", "Test", "Deploy"} == names
        # Sequential stages
        assert len(rels) == 2


class TestDockerCompose:
    def test_parse_services(self, analyzer):
        content = """
version: '3'
services:
  web:
    build: .
    depends_on:
      - db
      - redis
  db:
    image: postgres:15
  redis:
    image: redis:7
"""
        entities, rels = analyzer.analyze_file("docker-compose.yml", content)

        svc_names = {e.name for e in entities}
        assert {"web", "db", "redis"} == svc_names

        depends = [r for r in rels if r.relationship_type == "depends_on"]
        assert len(depends) == 2
