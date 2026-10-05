"""Check a document from the command line.

    python -m engine.cli check letter.pdf --applicant "Jane Doe" --other-party "John Doe" [--para 17] [--votes 3] [--llm offline]
    python -m engine.cli rules
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from engine.llm import get_llm
from engine.models import Application
from engine.pipeline import check_document
from engine.rules import load_rules


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("files", nargs="+")
    c.add_argument("--applicant", required=True)
    c.add_argument("--other-party")
    c.add_argument("--para", help="Schedule 1 paragraph the provider relies on")
    c.add_argument("--votes", type=int)
    c.add_argument("--llm", choices=["anthropic", "offline"])
    c.add_argument("--cache", choices=["off", "on", "replay"])
    sub.add_parser("rules")
    a = ap.parse_args(argv)

    if a.cmd == "rules":
        rs = load_rules()
        for r in rs.rules.values():
            print(f"{r.paragraph:>3}  {r.id:<28} {len(r.elements)} elements  {r.short_name}")
        return 0

    rules = load_rules()
    llm = get_llm(a.llm, a.cache)
    app = Application(applicant_name=a.applicant, other_party_name=a.other_party)

    async def run():
        out = []
        for i, f in enumerate(a.files, 1):
            p = Path(f)
            res = await check_document(p.read_bytes(), p.name, app, rules=rules, llm=llm, votes=a.votes, claimed_para=a.para, document_id=f"D{i}")
            out.append(res.model_dump())
        return out

    results = asyncio.run(run())
    json.dump(results if len(results) > 1 else results[0], sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
