"""Typed schema for repo-manifest.json.

The manifest generator produces this structure. Rego policies consume it.
Pydantic validates the shape — wrong field names or types are caught at
generation time, not at policy evaluation time.
"""

from __future__ import annotations

from pydantic import BaseModel


class ManifestFiles(BaseModel):
    pyrightconfig: bool
    ruff: bool
    gitleaks: bool
    sops: bool
    trivy: bool
    mega_linter: bool
    mega_linter_extends_url: str | None
    conftest_toml: bool
    editorconfig: bool
    tsconfig: bool
    eslint_config: bool
    pre_commit_config: bool
    commitlint_config: bool
    gitignore: bool
    gitignore_covers_decrypted: bool
    ci_json: bool
    renovate: bool
    nvmrc: bool
    envrc: bool
    makefile: bool
    env_example: bool
    gitignore_covers_spikes: bool


class ManifestDirectories(BaseModel):
    tests: bool
    secrets: bool
    decrypted: bool
    github_workflows: bool
    gitea_workflows: bool


class ManifestContent(BaseModel):
    python_files: int
    typescript_files: int
    javascript_files: int
    shell_files: int
    compose_files: int
    shell_scripts_over_30_lines: int
    justfile_recipes_over_10_lines: int
    dockerfile_files: int
    python_files_with_hyphens: int
    pre_commit_hooks: list[str]
    max_blast_radius: int
    max_naming_entropy: float


class ManifestDependencies(BaseModel):
    pytest_randomly: bool
    test_deps_defined: bool
    eslint_plugin_jest: bool
    zod: bool
    pydantic: bool
    import_linter: bool
    import_linter_configured: bool
    hypothesis: bool
    stryker: bool
    i18n_framework: bool
    structured_logging_js: bool
    structured_logging_py: bool
    opentelemetry: bool


class ManifestCI(BaseModel):
    workflow_uses_composite_action: bool
    workflow_fetch_depth_zero: bool
    workflow_persist_credentials_false: bool
    workflow_actions_sha_pinned: bool
    has_sha_pins: bool
    ci_delegates_to_runner: bool
    ci_mixes_schedule_and_push: bool
    ci_run_blocks_over_10_lines: int
    run_blocks_have_groups: bool = True
    push_trigger_all_branches: bool = True
    github_token_workaround: bool = True
    has_scheduled_dockle: bool = False


class ManifestSuppressions(BaseModel):
    noqa: int
    type_ignore: int
    nosemgrep: int
    shellcheck_disable: int
    trivyignore: int
    gitleaksignore: int
    total: int


class ManifestObservability(BaseModel):
    is_service: bool
    has_health_route: bool
    has_metrics: bool
    has_error_tracking: bool
    has_tracing: bool


class Manifest(BaseModel):
    files: ManifestFiles
    directories: ManifestDirectories
    content: ManifestContent
    dependencies: ManifestDependencies
    ci: ManifestCI
    observability: ManifestObservability
    acknowledged: dict
    suppressions: ManifestSuppressions
