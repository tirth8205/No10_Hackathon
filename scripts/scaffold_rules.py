#!/usr/bin/env python3
"""Write a first-draft rule YAML for every Schedule 1 paragraph, using the element
tables and mutation reasons in generate_da_evidence.py so the element ids match the
test data exactly. Existing files are left alone unless --force is given.

    .venv/bin/python scripts/scaffold_rules.py [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from generate_da_evidence import PARAS  # noqa: E402

RULES = ROOT / "rules"

SLUG = {
    "1": "arrest", "2": "caution", "3": "proceedings", "4": "conviction", "5": "bind_over",
    "6": "dvpn", "6A": "dapn", "7": "injunction", "8": "undertaking", "9": "finding_of_fact",
    "10": "expert_report", "11": "health_prof", "12": "health_referral", "13": "marac",
    "14": "idva", "15": "isva", "16": "la_housing", "17": "support_org", "18": "refuge_refusal",
    "19": "public_authority", "20": "home_office", "21": "economic_abuse",
}
GUIDANCE = {
    "1": "2.16 to 2.20", "2": "2.21 to 2.24", "3": "2.25 to 2.28", "4": "2.29 to 2.31", "5": "2.32 to 2.34",
    "6": "2.35 to 2.36", "6A": "2.37", "7": "2.38 to 2.42", "8": "2.43 to 2.46", "9": "2.47 to 2.49",
    "10": "2.50 to 2.51", "11": "2.52 to 2.60", "12": "2.61 to 2.65", "13": "2.66 to 2.67", "14": "2.68",
    "15": "2.69", "16": "2.70 to 2.73", "17": "2.74 to 2.77", "18": "2.78 to 2.82", "19": "2.83 to 2.85",
    "20": "2.86", "21": "2.87 to 2.93",
}
# Whose abuse the evidence can be about (docs/06 section 6.1) and whether B must be named.
APPLICANT_ONLY = {"11", "12", "14", "15", "17", "20", "21"}
B_NOT_REQUIRED = {"11", "12", "14", "17", "20"}
# Elements that cannot be confirmed from the text alone: missing -> needs_caseworker.
UNVERIFIABLE = {("1", "acceptable_source"), ("6A", "valid_notice"), ("10", "expert_identity_and_qualifications"),
                ("11", "appropriate_health_professional"), ("21", "corroboration_or_explanation")}
SHARE = {"17": 0.43, "7": 0.24, "11": 0.09, "14": 0.08}


def rule_id(code: str) -> str:
    return f"sch1_p{code.lower()}_{SLUG[code]}"


def build(code: str) -> dict:
    spec = PARAS[code]
    elements = []
    for eid, desc in spec["elements"].items():
        reasons = [m["why"] for m in spec["mutations"].values() if m["element"] == eid and m["status"] != "met"]
        elements.append({
            "id": eid,
            "label": desc.split(" (")[0][:60],
            "requirement": desc + ".",
            "accept_if": "The document clearly shows this, in any wording where the meaning is clear.",
            "reject_if": " ".join(reasons) if reasons else "The document does not show this.",
            "fix": f"Ask the author to confirm: {desc[0].lower() + desc[1:]}.",
            **({"unverifiable_to_caseworker": True} if (code, eid) in UNVERIFIABLE else {}),
        })
    always_refer = code == "21"
    return {
        "id": rule_id(code),
        "gateway": "da",
        "enabled": True,
        "paragraph": code,
        "legal_ref": f"Civil Legal Aid (Procedure) Regulations 2012, Schedule 1, paragraph {code}",
        "guidance_ref": f"LAA Evidence Requirements v15, paragraphs {GUIDANCE[code]}",
        "name": spec["title"],
        "short_name": spec["title"][:50],
        **({"share_of_applications": SHARE[code]} if code in SHARE else {}),
        "names_other_party_required": code not in B_NOT_REQUIRED,
        "applicant_must_be_victim": code in APPLICANT_ONLY,
        "always_needs_caseworker": always_refer,
        "accepted_formats": ["letter"],
        "classification_hints": [spec["title"]],
        "elements": elements,
        "hedge_terms": [],
        "gov_template_url": None,
        "test_cases_min": 5,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", default=None, help="paragraph codes to write")
    a = ap.parse_args()
    RULES.mkdir(exist_ok=True)
    for code in PARAS:
        if a.only and code not in a.only:
            continue
        path = RULES / f"{rule_id(code)}.yaml"
        if path.exists() and not a.force:
            print("skip", path.name)
            continue
        path.write_text(yaml.safe_dump(build(code), sort_keys=False, allow_unicode=True, width=120))
        print("wrote", path.name)


if __name__ == "__main__":
    main()
