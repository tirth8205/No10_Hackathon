"""Demo only: set classification.letter_date on a document's stored result (same lock workaround as synth_result2.py).
Why: both of Jane's letters are dated 29 September, and the web app orders versions by letterDate string with
upload order as the tie-break, so the weak letter showed as the 'newer version'. Writing the weak letter's date
in ISO form ("2026-09-29", the engine's usual form; it still displays as "29 September") makes it sort older.
Usage: .venv/bin/python pitch/tools/set_letter_date.py <document_id> <date>
"""
import json, sqlite3, sys, threading, time, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core import store  # noqa: E402
doc_id, date = sys.argv[1], sys.argv[2]
doc = store._one("SELECT * FROM documents WHERE id=?", (doc_id,))
r = json.loads(doc["result_json"]); r["classification"]["letter_date"] = date
case = store._one("SELECT * FROM cases WHERE id=?", (doc["case_id"],))
sel = json.loads(case.get("selected_json") or "[]")
stop = threading.Event()
def poke():
    while not stop.is_set():
        try:
            urllib.request.urlopen(urllib.request.Request(f"http://localhost:8000/web/cases/{doc['case_id']}/selection", method="PUT",
                data=json.dumps({"documentIds": sel}).encode(), headers={"content-type": "application/json"}), timeout=10).read()
        except Exception:
            pass
        time.sleep(0.05)
threading.Thread(target=poke, daemon=True).start()
conn = sqlite3.connect(store.path, timeout=120, isolation_level=None)
conn.execute("BEGIN IMMEDIATE"); stop.set()
conn.execute("UPDATE documents SET result_json=? WHERE id=?", (json.dumps(r, ensure_ascii=False), doc_id))
conn.execute("COMMIT"); print("ok", doc_id, date)
