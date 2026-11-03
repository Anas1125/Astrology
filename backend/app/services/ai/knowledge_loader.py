"""Load and validate versioned interpretation knowledge files."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from pydantic import ValidationError

from app.services.ai.contracts import InterpretationRule
from app.services.ai.rule_matcher import validate_rule_conditions

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
RULE_FILE_SUFFIXES = {".json", ".yaml", ".yml"}


class KnowledgeBaseError(ValueError):
    """A knowledge file is malformed, inconsistent or insufficiently attributed."""


def _read_document(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise KnowledgeBaseError(f"Cannot read knowledge file {path}: {exc}") from exc
    try:
        if path.suffix.lower() == ".json":
            return json.loads(raw)
        if path.suffix.lower() in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:
                raise KnowledgeBaseError("YAML knowledge files require PyYAML to be installed") from exc
            return yaml.safe_load(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise KnowledgeBaseError(f"Invalid structured data in {path}: {exc}") from exc
    raise KnowledgeBaseError(f"Unsupported knowledge file extension: {path.suffix}")


def _validate_provenance(rule: InterpretationRule, path: Path) -> None:
    provenance = rule.provenance
    if not provenance.source_name.strip() or not provenance.attribution.strip() or not provenance.reference.strip():
        raise KnowledgeBaseError(f"Rule {rule.rule_id} in {path} must include source attribution and reference")
    placeholders = {"n/a", "na", "none", "unknown", "unsourced", "test", "test only"}
    if provenance.editorial_status != "test_only" and (
        any(value.strip().casefold() in placeholders for value in (provenance.source_name, provenance.attribution, provenance.reference))
        or len(provenance.source_name.strip()) < 3
        or len(provenance.attribution.strip()) < 3
        or len(provenance.reference.strip()) < 12
    ):
        raise KnowledgeBaseError(f"Rule {rule.rule_id} in {path} has inadequate source attribution")


def load_knowledge_base(source: str | Path) -> tuple[str, tuple[InterpretationRule, ...]]:
    """Load a file or a tree of JSON/YAML documents with globally unique IDs."""
    root = Path(source)
    if not root.exists():
        raise KnowledgeBaseError(f"Knowledge path does not exist: {root}")
    paths = [root] if root.is_file() else sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in RULE_FILE_SUFFIXES
    )
    if not paths:
        raise KnowledgeBaseError(f"No JSON or YAML knowledge files found in {root}")

    all_rules: list[InterpretationRule] = []
    base_version: str | None = None
    seen: set[str] = set()
    for path in paths:
        document = _read_document(path)
        if not isinstance(document, dict):
            raise KnowledgeBaseError(f"Knowledge document {path} must be an object")
        version = document.get("knowledge_base_version")
        if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
            raise KnowledgeBaseError(f"Knowledge document {path} has an invalid knowledge_base_version")
        if base_version is None:
            base_version = version
        elif version != base_version:
            raise KnowledgeBaseError(
                f"Knowledge base version mismatch in {path}: expected {base_version}, got {version}"
            )
        raw_rules = document.get("rules")
        if not isinstance(raw_rules, list):
            raise KnowledgeBaseError(f"Knowledge document {path} must contain a rules list")
        for index, raw_rule in enumerate(raw_rules):
            try:
                rule = InterpretationRule.model_validate(raw_rule)
            except ValidationError as exc:
                message = "; ".join(
                    f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}" for issue in exc.errors()
                )
                raise KnowledgeBaseError(f"Invalid rule {index} in {path}: {message}") from exc
            if rule.knowledge_base_version != version:
                raise KnowledgeBaseError(
                    f"Rule {rule.rule_id} in {path} declares knowledge base version {rule.knowledge_base_version}, expected {version}"
                )
            if rule.division is not None:
                supported_divisions = {"D1", "D9"} if rule.system.value == "vedic" else {"W", "natal", "NATAL"}
                if rule.division not in supported_divisions:
                    raise KnowledgeBaseError(f"Rule {rule.rule_id} in {path} has unsupported division {rule.division!r}")
            if rule.rule_id in seen:
                raise KnowledgeBaseError(f"Duplicate rule ID: {rule.rule_id}")
            seen.add(rule.rule_id)
            _validate_provenance(rule, path)
            try:
                validate_rule_conditions(rule)
            except ValueError as exc:
                raise KnowledgeBaseError(f"Invalid conditions in rule {rule.rule_id} in {path}: {exc}") from exc
            all_rules.append(rule)
    assert base_version is not None
    return base_version, tuple(all_rules)
