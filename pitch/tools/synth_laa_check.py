"""Demo only: replace a submission's stored LAA independent re-check (submissions.laa_check_json /
differences_json, written by app.core.laa_check with the offline stub) with the agreeing result a live
re-check gives: the snapshot's own (synthesised) result, differences []. Marked model="demo-synthesised".
Usage: .venv/bin/python pitch/tools/synth_laa_check.py <submission_id>
"""
import json, sqlite3, sys, threading, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core import store  # noqa: E402 (reads only)

sid = sys.argv[1]
sub = store._one("SELECT * FROM submissions WHERE id=?", (sid,))
snap = json.loads(sub["snapshot_json"]) if "snapshot_json" in sub else None
if snap is None:
    raise SystemExit(f"columns: {list(sub)}")
docs = []
for d in snap["documents"]:
    r = dict(d["result"]); r["document_id"] = d["document_id"]; r["filename"] = d["filename"]; r["model"] = "demo-synthesised"
    docs.append(r)
check = {"documents": docs, "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
case = store._one("SELECT * FROM cases WHERE id=?", (sub["case_id"],))
sel = json.loads(case.get("selected_json") or "[]")
stop = threading.Event()
def poke():
    while not stop.is_set():
        try:
            urllib.request.urlopen(urllib.request.Request(f"http://localhost:8000/web/cases/{sub['case_id']}/selection", method="PUT",
                data=json.dumps({"documentIds": sel}).encode(), headers={"content-type": "application/json"}), timeout=10).read()
        except Exception:
            pass
        time.sleep(0.05)
threading.Thread(target=poke, daemon=True).start()
conn = sqlite3.connect(store.path, timeout=120, isolation_level=None)
conn.execute("BEGIN IMMEDIATE"); stop.set()
conn.execute("UPDATE submissions SET laa_check_json=?, differences_json=? WHERE id=?", (json.dumps(check, ensure_ascii=False), "[]", sid))
conn.execute("COMMIT")
print(json.dumps({"submission": sid, "documents": [d["document_id"] for d in docs], "differences": 0}))
