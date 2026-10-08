"""Demo only: replace a document's check result with one synthesised by the Claude CLI.

The backend has no API key here, so the offline stub misreads letters. For the pitch videos we
ask `claude -p` to write the result the live engine would give, in the engine's own shape, and
store it. The result is marked model="demo-synthesised" so it is never mistaken for a live check.

Usage: .venv/bin/python pitch/tools/synth_result.py <document_id> [rule_id]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core import store  # noqa: E402

doc_id = sys.argv[1]
rule_id = sys.argv[2] if len(sys.argv) > 2 else "sch1_p17_support_org"

doc = store.get_document(doc_id)
if not doc:
    raise SystemExit(f"no document {doc_id}")
text = store.document_text(doc_id) or ""
case = store._one("SELECT * FROM cases WHERE id=?", (doc["case_id"],))
current = doc.get("result") or {}
rule = (ROOT / "rules" / f"{rule_id}.yaml").read_text()
template = store._one(
    "SELECT result_json FROM documents WHERE result_json LIKE ? AND id<>? LIMIT 1",
    (f'%"rule_id": "{rule_id}"%', doc_id),
)

prompt = f"""You are the evidence check in a legal aid tool. Produce the check result for one letter as JSON ONLY (no prose, no code fence).

Rule (YAML, the requirements to check, element ids and labels must come from here):
{rule}

The letter's text:
<<<
{text}
>>>

Case: applicant {case.get('applicant_name') or case.get('applicantName')}, other party {case.get('other_party_name') or case.get('otherPartyName')}.

Output exactly the same keys and shapes as this example result from the same engine (copy its structure; write fresh values for THIS letter):
{template['result_json'] if template else json.dumps(current)}

Rules for the values:
- rule_id "{rule_id}", claimed_rule_id "{rule_id}", recategorise_to null; classification.rule_id "{rule_id}", confidence "high", with author_name/author_org/author_role/letter_date read from the letter; rationale one plain sentence.
- One element per requirement in the rule, element_id and label from the rule. status is "included", "missing" or "unclear". quote is a verbatim sentence or clause copied exactly from the letter (null when missing); quote_verified true when quoted; votes {{"included":3,"missing":0,"unclear":0}} style, consistent with status; reasoning one plain-English sentence a solicitor would accept (never mention stubs, keywords or AI).
- A sentence that only names a source of information (e.g. "Victim testimony and referral.") does NOT state the specific matters relied on: that element is "missing" with quote null.
- For missing elements: fix = what the writer should add, in one sentence; client_hint = a short, kind, plain-English phrase for the client, written as a full sentence starting with a capital letter.
- verdict "meets" if every element is included, else "needs_change". provider_summary like "Paragraph 17, support organisation letter: 7 of 8 requirements included. Missing: specific matters relied on." client_message: for meets, "Your letter is ready. Your solicitor will check it and send it in."; otherwise "The legal aid rules ask for one thing that isn't in the letter yet." (adjust "one thing" to the count).
- request_letter: a short, polite letter to the author (by name and organisation) asking them to add exactly what is missing, quoting what the rules ask for; empty string when verdict is meets.
- flags [], name_check null, keep verification entries in the example's shape but describe this letter's details; model "demo-synthesised", votes 3, votes_failed 0, latency_ms 18000, rules_version as in the example.
"""

out = subprocess.run(["claude", "-p", prompt, "--output-format", "text"], capture_output=True, text=True, timeout=600)
if out.returncode != 0:
    raise SystemExit(out.stderr)
raw = out.stdout.strip()
raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
result = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])

for e in result.get("elements", []):
    if e.get("quote") and e["quote"] not in " ".join(text.split()) and e["quote"] not in text:
        print(f"warning: quote not verbatim for {e.get('element_id')}: {e['quote'][:60]}", file=sys.stderr)
result["document_id"] = doc_id
result["filename"] = current.get("filename") or result.get("filename")
result["model"] = "demo-synthesised"
store.set_document_result(doc_id, result)
print(json.dumps({"document_id": doc_id, "verdict": result["verdict"], "summary": result.get("provider_summary")}))
