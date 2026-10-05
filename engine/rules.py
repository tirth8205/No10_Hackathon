"""Load and validate the evidence rules held as YAML in rules/.

Rules are data, not code: adding an evidence type means adding a YAML file and
its test cases. Every file is validated at load time and a bad rule fails loudly.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
GATEWAY_FILE = "_gateway_da.yaml"


class Element(BaseModel):
    id: str
    label: str
    requirement: str
    accept_if: str
    reject_if: str
    fix: str
    # Plain words for the client, e.g. "say why you needed their help". Optional.
    client_hint: str | None = None
    # "flag" elements never make the document fail; they only add a warning.
    kind: str = Field(default="required", pattern="^(required|flag)$")
    # If the element cannot be confirmed from the text alone (e.g. a registration
    # number), a missing result is downgraded to needs_caseworker, not needs_change.
    unverifiable_to_caseworker: bool = False


class Rule(BaseModel):
    id: str
    gateway: str = "da"
    enabled: bool = True
    legal_ref: str
    guidance_ref: str
    name: str
    short_name: str
    paragraph: str
    share_of_applications: float | None = None
    names_other_party_required: bool = False
    applicant_must_be_victim: bool = True
    # Paragraph 21 (economic abuse) is the Director's discretion: never "meets".
    always_needs_caseworker: bool = False
    accepted_formats: list[str] = Field(default_factory=list)
    classification_hints: list[str] = Field(default_factory=list)
    elements: list[Element]
    hedge_terms: list[str] = Field(default_factory=list)
    gov_template_url: str | None = None
    test_cases_min: int = 0

    def element(self, element_id: str) -> Element | None:
        return next((e for e in self.elements if e.id == element_id), None)

    @property
    def required_elements(self) -> list[Element]:
        return [e for e in self.elements if e.kind == "required"]

    def prompt_fingerprint(self) -> str:
        """Only what the assessment prompt sees; cosmetic fields (labels, hints, fixes) do not invalidate caches."""
        import json

        return json.dumps({"id": self.id, "name": self.name, "legal_ref": self.legal_ref, "guidance_ref": self.guidance_ref,
                           "hedge_terms": self.hedge_terms,
                           "elements": [[e.id, e.requirement, e.accept_if, e.reject_if] for e in self.elements]}, sort_keys=True)


class Gateway(BaseModel):
    id: str = "da"
    name: str
    rules_version: str
    guidance_version: str
    name_match_threshold: int = 85
    quote_fuzzy_threshold: int = 90
    hedge_terms: list[str] = Field(default_factory=list)
    injection_markers: list[str] = Field(default_factory=list)
    placeholder_patterns: list[str] = Field(default_factory=list)


class RuleSet(BaseModel):
    gateway: Gateway
    rules: dict[str, Rule]

    def enabled(self) -> list[Rule]:
        return [r for r in self.rules.values() if r.enabled]

    def get(self, rule_id: str) -> Rule | None:
        return self.rules.get(rule_id)


class RuleLoadError(RuntimeError):
    pass


def load_rules(rules_dir: Path | str = RULES_DIR) -> RuleSet:
    rules_dir = Path(rules_dir)
    gateway_path = rules_dir / GATEWAY_FILE
    if not gateway_path.exists():
        raise RuleLoadError(f"missing gateway config {gateway_path}")
    try:
        gateway = Gateway.model_validate(yaml.safe_load(gateway_path.read_text()) or {})
    except ValidationError as e:
        raise RuleLoadError(f"{gateway_path.name}: {e}") from e

    rules: dict[str, Rule] = {}
    for path in sorted(rules_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue
        try:
            rule = Rule.model_validate(yaml.safe_load(path.read_text()) or {})
        except ValidationError as e:
            raise RuleLoadError(f"{path.name}: {e}") from e
        if rule.id != path.stem:
            raise RuleLoadError(f"{path.name}: id '{rule.id}' must match the file name")
        if rule.id in rules:
            raise RuleLoadError(f"duplicate rule id {rule.id}")
        ids = [e.id for e in rule.elements]
        if len(ids) != len(set(ids)):
            raise RuleLoadError(f"{path.name}: duplicate element ids")
        if not rule.required_elements:
            raise RuleLoadError(f"{path.name}: a rule needs at least one required element")
        rules[rule.id] = rule
    if not rules:
        raise RuleLoadError(f"no rules found in {rules_dir}")
    return RuleSet(gateway=gateway, rules=rules)
