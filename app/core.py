"""Shared state for the API routers: the store, the loaded rules and LLM, and the
background check runner. Both app.main (engine-shaped API) and app.web_api
(frontend-shaped API) import from here.
"""
from __future__ import annotations

from typing import Any

from app.store import Store, now
from engine.ingest import Ingested
from engine.llm import get_llm
from engine.models import Application
from engine.pipeline import check_text
from engine.rules import RuleSet, load_rules

store = Store()
state: dict[str, Any] = {"rules": load_rules(), "llm": get_llm()}


def rules() -> RuleSet:
    return state["rules"]


def application_for(case: dict) -> Application:
    return Application(applicant_name=case["applicant_name"] or "", other_party_name=case["other_party_name"] or None,
                       case_type=case.get("case_type"), application_date=case.get("application_date"))


async def run_check(case: dict, doc: dict, text: str, needs_transcription: bool = False,
                    files: list[tuple[bytes, str]] | None = None) -> None:
    """Transcribe if needed, run the engine, store the result. Never raises: errors land on the document."""
    llm = state["llm"]
    try:
        if needs_transcription and files:
            parts = []
            for data, media_type in files:
                tr = await llm.transcribe(data, media_type)
                if tr.text.strip():
                    parts.append(tr.text)
            if parts:
                text = "\n\n".join(parts)
                store.set_document_text(doc["id"], text)
        # a scan or photo that yielded no text must go to a caseworker as illegible, not be classified as "not prescribed"
        ing = Ingested(text=text, kind="scan", needs_transcription=True) if needs_transcription else None
        res = await check_text(text, doc["filename"], application_for(case), rules=rules(), llm=llm,
                               claimed_para=doc.get("claimed_para"), document_id=doc["id"], ingested=ing)
        store.set_document_result(doc["id"], res.model_dump())
    except Exception as e:  # surface, never hang the UI
        store.set_document_result(doc["id"], None, f"{type(e).__name__}: {e}")


async def recheck_case(case: dict) -> None:
    """Re-run every held document after the case details change."""
    for d in store.list_documents(case["id"]):
        text = store.document_text(d["id"])
        if text:
            store._exec("UPDATE documents SET status='checking' WHERE id=?", (d["id"],))
            await run_check(case, d, text)


async def laa_check(submission: dict) -> None:
    """Link 2: the LAA runs its own check on the pack it received (the submission snapshot, not the
    live case) and records every element or verdict that differs from the provider's result.
    Never raises: a document that cannot be checked is recorded as an error. Both /api and /web
    submissions schedule this in the background."""
    snap = submission["snapshot"]
    app_ = Application(**snap["application"])
    results, diffs = [], []
    for d in snap["documents"]:
        text = d["snapshot_text"] if "snapshot_text" in d else store.document_text(d["document_id"])
        if not text:
            results.append({"document_id": d["document_id"], "error": "text no longer held"})
            continue
        try:
            res = await check_text(text, d["filename"], app_, rules=rules(), llm=state["llm"], claimed_para=d.get("claimed_para"), document_id=d["document_id"])
        except Exception as e:
            results.append({"document_id": d["document_id"], "error": f"{type(e).__name__}: {e}"})
            continue
        r = res.model_dump()
        results.append(r)
        prov = {e["element_id"]: e["status"] for e in d["result"].get("elements", [])}
        laa = {e["element_id"]: e["status"] for e in r["elements"]}
        for k in sorted(set(prov) | set(laa)):
            if prov.get(k) != laa.get(k):
                diffs.append({"document_id": d["document_id"], "element_id": k, "provider": prov.get(k), "laa": laa.get(k)})
        if d["result"]["verdict"] != r["verdict"]:
            diffs.append({"document_id": d["document_id"], "element_id": None, "provider": d["result"]["verdict"], "laa": r["verdict"]})
    store.set_laa_check(submission["id"], {"documents": results, "checked_at": now()}, diffs)


def case_verdict(docs: list[dict]) -> str:
    verdicts = [d["verdict"] for d in docs if d.get("verdict")]
    if "meets" in verdicts:
        return "meets"
    if "needs_caseworker" in verdicts:
        return "needs_caseworker"
    if "needs_change" in verdicts:
        return "needs_change"
    return "no_evidence_yet"
