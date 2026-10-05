"""Run the engine over the labelled test sets and report accuracy.

    python -m eval.run_eval --set synthetic --votes 3            # develop against this
    python -m eval.run_eval --set gold --votes 3                 # run ONCE at the end
    python -m eval.run_eval --set both --para 17 18 --limit 20 --llm offline

The test data uses pass/fail/refer and met/not_met/unclear; the engine uses
meets/needs_change/needs_caseworker and included/missing/unclear. Mapped here.

Writes eval/results/<name>.json, eval/results/latest.json and eval/results/failures.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from engine.llm import get_llm
from engine.models import Application
from engine.pipeline import check_text
from engine.rules import load_rules

ROOT = Path(__file__).resolve().parent.parent
DATA = {"synthetic": ROOT / "data" / "synthetic_cases.json", "gold": ROOT / "data" / "moj_gold_cases.json"}
RESULTS = ROOT / "eval" / "results"

OUTCOME = {"pass": "meets", "fail": "needs_change", "refer": "needs_caseworker"}
STATUS = {"met": "included", "not_met": "missing", "unclear": "unclear"}


def load_cases(which: str, paras: list[str] | None, limit: int | None, ids: list[str] | None) -> list[dict]:
    files = [DATA["synthetic"], DATA["gold"]] if which == "both" else [DATA[which]]
    cases = []
    for f in files:
        cases += json.load(open(f))["cases"]
    if ids:
        cases = [c for c in cases if c["id"] in set(ids)]
    if paras:
        want = {p.upper() for p in paras}
        cases = [c for c in cases if any(d["claimed_para"].upper() in want for d in c["documents"])]
    return cases[:limit] if limit else cases


async def run_case(case: dict, rules, llm, votes: int, sem: asyncio.Semaphore) -> dict:
    app = Application(applicant_name=case["application"]["applicant"], other_party_name=case["application"].get("other_party"))
    docs_out = []
    for d in case["documents"]:
        async with sem:
            t0 = time.perf_counter()
            try:
                res = await check_text(d["text"], f"{case['id']}-{d['doc_id']}.txt", app, rules=rules, llm=llm, votes=votes,
                                       claimed_para=d["claimed_para"], document_id=d["doc_id"])
                err = None
            except Exception as e:  # keep going; record the failure
                res, err = None, f"{type(e).__name__}: {e}"
        exp = d["expected"]
        expected_verdict = OUTCOME[exp["outcome"]]
        predicted = res.verdict if res else "error"
        el_exp = {k: STATUS[v["status"]] for k, v in exp["elements"].items()}
        el_pred = {e.element_id: e.status for e in res.elements} if res else {}
        el_match = {k: (el_pred.get(k) == v) for k, v in el_exp.items()}
        recat_exp = exp.get("recategorise_to")
        recat_pred = None
        if res and res.recategorise_to:
            r = rules.get(res.recategorise_to)
            recat_pred = r.paragraph if r else None
        docs_out.append({
            "doc_id": d["doc_id"], "claimed_para": d["claimed_para"], "expected": expected_verdict, "predicted": predicted,
            "agree": predicted == expected_verdict,
            "safe_agree": predicted == expected_verdict or (expected_verdict == "needs_change" and predicted == "needs_caseworker"),
            "false_approval": expected_verdict != "meets" and predicted == "meets",
            "false_rejection": expected_verdict == "meets" and predicted in ("needs_change", "not_prescribed"),
            "elements_expected": el_exp, "elements_predicted": el_pred, "element_matches": el_match,
            "recategorise_expected": recat_exp, "recategorise_predicted": recat_pred,
            "flags": res.flags if res else [], "reason_expected": exp.get("reason"), "error": err,
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "quotes_unverified": sum(1 for e in (res.elements if res else []) if e.status == "included" and not e.quote_verified),
        })
    exp_case = OUTCOME[case["expected_overall"]]
    verdicts = [x["predicted"] for x in docs_out]
    pred_case = "meets" if "meets" in verdicts else "needs_caseworker" if "needs_caseworker" in verdicts else "needs_change" if "needs_change" in verdicts else verdicts[0] if verdicts else "error"
    return {"id": case["id"], "category": case.get("category"), "expected_case": exp_case, "predicted_case": pred_case,
            "case_agree": exp_case == pred_case, "documents": docs_out}


def summarise(runs: list[dict]) -> dict:
    docs = [d for r in runs for d in r["documents"]]
    n = len(docs) or 1
    not_meets = [d for d in docs if d["expected"] != "meets"] or [None]
    meets = [d for d in docs if d["expected"] == "meets"] or [None]
    el_total = sum(len(d["element_matches"]) for d in docs) or 1
    el_ok = sum(sum(1 for v in d["element_matches"].values() if v) for d in docs)
    recat = [d for d in docs if d["recategorise_expected"]]
    lat = [d["latency_ms"] for d in docs]

    def group(key):
        out = {}
        for k, items in sorted(defaultdict(list, _group(docs, key)).items()):
            m = len(items)
            out[k] = {"n": m, "agreement": round(sum(x["agree"] for x in items) / m, 3),
                      "false_approvals": sum(x["false_approval"] for x in items),
                      "false_rejections": sum(x["false_rejection"] for x in items),
                      "to_caseworker": sum(x["predicted"] == "needs_caseworker" for x in items)}
        return out

    confusion = Counter((d["expected"], d["predicted"]) for d in docs)
    return {
        "documents": len(docs), "cases": len(runs),
        "agreement": round(sum(d["agree"] for d in docs) / n, 3),
        "safe_agreement": round(sum(d["safe_agree"] for d in docs) / n, 3),
        "case_agreement": round(sum(r["case_agree"] for r in runs) / (len(runs) or 1), 3),
        "false_approval_rate": round(sum(d["false_approval"] for d in docs) / len([x for x in not_meets if x]) if not_meets[0] else 0, 3),
        "false_rejection_rate": round(sum(d["false_rejection"] for d in docs) / len([x for x in meets if x]) if meets[0] else 0, 3),
        "caseworker_routing_rate": round(sum(d["predicted"] == "needs_caseworker" for d in docs) / n, 3),
        "element_accuracy": round(el_ok / el_total, 3),
        "recategorisation_accuracy": round(sum(d["recategorise_predicted"] == d["recategorise_expected"] for d in recat) / len(recat), 3) if recat else None,
        "quote_validity": round(1 - sum(d["quotes_unverified"] for d in docs) / max(1, sum(sum(1 for s in d["elements_predicted"].values() if s == "included") for d in docs)), 3),
        "errors": sum(1 for d in docs if d["error"]),
        "latency_ms_p50": int(statistics.median(lat)) if lat else 0,
        "latency_ms_p95": int(sorted(lat)[int(len(lat) * 0.95) - 1]) if len(lat) >= 2 else (lat[0] if lat else 0),
        "by_paragraph": group("claimed_para"),
        "by_category": {k: v for k, v in group("category").items()},
        "confusion": {f"{e}->{p}": c for (e, p), c in sorted(confusion.items())},
    }


def _group(docs, key):
    g = defaultdict(list)
    for d in docs:
        g[d.get(key) or d.get("_case_" + key) or "?"].append(d)
    return g


def failures_md(runs: list[dict]) -> str:
    lines = ["# Disagreements", ""]
    for r in runs:
        for d in r["documents"]:
            if d["agree"] and all(d["element_matches"].values()):
                continue
            lines.append(f"## {r['id']} / {d['doc_id']} (para {d['claimed_para']})")
            lines.append(f"- expected **{d['expected']}**, predicted **{d['predicted']}**" + (f" (error: {d['error']})" if d["error"] else ""))
            if d["reason_expected"]:
                lines.append(f"- label reason: {d['reason_expected']}")
            diffs = [f"{k}: expected {d['elements_expected'][k]}, got {d['elements_predicted'].get(k)}" for k, ok in d["element_matches"].items() if not ok]
            if diffs:
                lines.append("- elements: " + "; ".join(diffs))
            if d["flags"]:
                lines.append("- flags: " + ", ".join(d["flags"]))
            lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["synthetic", "gold", "both"], default="synthetic")
    ap.add_argument("--votes", type=int, default=None)
    ap.add_argument("--para", nargs="*")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--llm", choices=["anthropic", "offline"])
    ap.add_argument("--cache", choices=["off", "on", "replay"])
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--name", default=None)
    a = ap.parse_args(argv)

    from engine.config import settings

    rules = load_rules()
    llm = get_llm(a.llm, a.cache)
    votes = a.votes or settings.votes
    cases = load_cases(a.set, a.para, a.limit, a.ids)
    for c in cases:
        for d in c["documents"]:
            d["_cat"] = c.get("category")
    print(f"{len(cases)} cases, llm={llm.name}, votes={votes}")

    async def go():
        sem = asyncio.Semaphore(a.concurrency)
        return await asyncio.gather(*[run_case(c, rules, llm, votes, sem) for c in cases])

    t0 = time.perf_counter()
    runs = asyncio.run(go())
    for r in runs:
        for d in r["documents"]:
            d["category"] = r["category"]
    summary = summarise(runs)
    summary.update({"set": a.set, "model": llm.name, "votes": votes, "rules_version": rules.gateway.rules_version,
                    "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "wall_seconds": round(time.perf_counter() - t0, 1)})
    RESULTS.mkdir(parents=True, exist_ok=True)
    name = a.name or f"{a.set}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out = {"summary": summary, "runs": runs}
    (RESULTS / f"{name}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    (RESULTS / "latest.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    (RESULTS / "failures.md").write_text(failures_md(runs))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("by_paragraph", "by_category", "confusion")}, indent=1))
    print("by paragraph:", json.dumps(summary["by_paragraph"]))
    print("confusion:", json.dumps(summary["confusion"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
