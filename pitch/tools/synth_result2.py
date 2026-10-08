"""Same as synth_result.py, but works while the running server holds SQLite's write lock.

The server's sweep_expired_text() leaves an implicit transaction open after every request, so
an outside writer only gets in during the instant the server commits. This script reads without
writing, asks `claude -p` for the result, then takes the write lock by waiting with a long busy
timeout while poking an idempotent server write (PUT selection with the case's current value).
Usage: .venv/bin/python pitch/tools/synth_result2.py <document_id> [rule_id]
"""
import json, re, secrets, sqlite3, subprocess, sys, threading, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core import store  # noqa: E402  (reads only)

doc_id = sys.argv[1]
rule_id = sys.argv[2] if len(sys.argv) > 2 else "sch1_p17_support_org"
doc = store._one("SELECT * FROM documents WHERE id=?", (doc_id,))
if not doc:
    raise SystemExit(f"no document {doc_id}")
text = doc.get("text") or ""
if not text:
    raise SystemExit("document text not available (expired?)")
case = store._one("SELECT * FROM cases WHERE id=?", (doc["case_id"],))
current = json.loads(doc["result_json"]) if doc.get("result_json") else {}
rule = (ROOT / "rules" / f"{rule_id}.yaml").read_text()
template = store._one("SELECT result_json FROM documents WHERE result_json LIKE ? AND id<>? AND result_json LIKE '%demo-synthesised%' LIMIT 1",
                      (f'%"rule_id": "{rule_id}"%', doc_id)) or store._one(
    "SELECT result_json FROM documents WHERE result_json LIKE ? AND id<>? LIMIT 1", (f'%"rule_id": "{rule_id}"%', doc_id))

src = (ROOT / "pitch/tools/synth_result.py").read_text()
prompt_tpl = src[src.index('prompt = f"""') + len('prompt = f"""'): src.index('"""\n\nout = ')]
prompt = eval('f"""' + prompt_tpl + '"""')  # same prompt as synth_result.py

out = subprocess.run(["claude", "-p", prompt, "--output-format", "text"], capture_output=True, text=True, timeout=600)
if out.returncode != 0:
    raise SystemExit(out.stderr)
raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", out.stdout.strip())
result = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
flat = " ".join(text.split())
for e in result.get("elements", []):
    if e.get("quote") and e["quote"] not in flat and e["quote"] not in text:
        print(f"warning: quote not verbatim for {e.get('element_id')}: {e['quote'][:60]}", file=sys.stderr)
result["document_id"] = doc_id
result["filename"] = current.get("filename") or result.get("filename")
result["model"] = "demo-synthesised"
result["checked_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

sel = json.loads(case.get("selected_json") or "[]")
stop = threading.Event()
def poke():
    while not stop.is_set():
        try:
            req = urllib.request.Request(f"http://localhost:8000/web/cases/{doc['case_id']}/selection", method="PUT",
                                         data=json.dumps({"documentIds": sel}).encode(), headers={"content-type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
        except Exception:
            pass
        time.sleep(0.05)
th = threading.Thread(target=poke, daemon=True); th.start()
conn = sqlite3.connect(store.path, timeout=120, isolation_level=None)
t0 = time.time()
conn.execute("BEGIN IMMEDIATE")
stop.set()
conn.execute("UPDATE documents SET status='done', verdict=?, result_json=? WHERE id=?", (result["verdict"], json.dumps(result, ensure_ascii=False), doc_id))
conn.execute("INSERT INTO tracker_events(id, case_id, event_type, applicant_text, solicitor_text, visible_to_applicant, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)",
             (secrets.token_hex(6), doc["case_id"], "document_checked", result.get("client_message", ""), result.get("provider_summary", ""), 1, "service", result["checked_at"]))
conn.execute("COMMIT")
print(f"lock after {time.time()-t0:.1f}s", file=sys.stderr)
print(json.dumps({"document_id": doc_id, "verdict": result["verdict"], "summary": result.get("provider_summary")}))
