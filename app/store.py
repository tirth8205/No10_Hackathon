"""Storage.

Two links, two kinds of record:

  Link 1 (applicant <-> solicitor): Case, Document (versioned), CheckResult, TrackerEvent,
         EvidenceRequest, ClientLink. Working records; the applicant and solicitor see
         different views of them.
  Link 2 (solicitor <-> LAA): Submission (a FROZEN snapshot of the chosen document
         versions, paragraphs and checklists), LAA independent check, Decision.
         A later upload never changes an earlier submission.

Document bytes and text live only in memory with a TTL. SQLite keeps verdicts,
quotes, snapshots and the audit log. Nothing uploaded is ever written to disk.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from engine.config import settings

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L


def neutral_ref(prefix: str = "LA") -> str:
    """Reveals nothing about the case: e.g. LA-7K4-29Q."""
    pick = lambda n: "".join(secrets.choice(_ALPHABET) for _ in range(n))  # noqa: E731
    return f"{prefix}-{pick(3)}-{pick(3)}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, ref TEXT UNIQUE, applicant_name TEXT, applicant_first_name TEXT, other_party_name TEXT,
  case_type TEXT, work_type TEXT, created_by TEXT, created_at TEXT, status TEXT DEFAULT 'open',
  safe_contact_method TEXT, safe_contact_value TEXT, safe_times TEXT, firm_id TEXT, firm_name TEXT, application_date TEXT,
  ask_label TEXT, selected_json TEXT, selection_touched INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, case_id TEXT, filename TEXT, uploaded_by TEXT, uploaded_at TEXT, claimed_para TEXT,
  replaces_document_id TEXT, version INTEGER DEFAULT 1, status TEXT, verdict TEXT, result_json TEXT, error TEXT,
  text_quality TEXT, purged INTEGER DEFAULT 0, pages_json TEXT, text TEXT
);
CREATE TABLE IF NOT EXISTS tracker_events (
  id TEXT PRIMARY KEY, case_id TEXT, event_type TEXT, applicant_text TEXT, solicitor_text TEXT,
  visible_to_applicant INTEGER DEFAULT 1, created_by TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS evidence_requests (
  id TEXT PRIMARY KEY, case_id TEXT, document_id TEXT, recipient TEXT, drafted_text TEXT, status TEXT,
  created_at TEXT, sent_at TEXT, reminder_at TEXT
);
CREATE TABLE IF NOT EXISTS client_links (
  token TEXT PRIMARY KEY, case_id TEXT, created_at TEXT, expires_at TEXT, revoked INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS submissions (
  id TEXT PRIMARY KEY, case_id TEXT, laa_ref TEXT, firm_name TEXT, submitted_at TEXT, document_ids_json TEXT,
  snapshot_json TEXT, notes TEXT, submit_anyway_reason TEXT, case_verdict TEXT, status TEXT,
  laa_check_json TEXT, differences_json TEXT, resubmission_of TEXT
);
CREATE TABLE IF NOT EXISTS decisions (
  id TEXT PRIMARY KEY, submission_id TEXT, caseworker TEXT, action TEXT, note TEXT, agreed_with_tool INTEGER,
  tool_verdict TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, actor TEXT, action TEXT, record TEXT, detail_json TEXT
);
"""


class Store:
    def __init__(self, path: Path | str | None = None):
        self.path = str(path or settings.db_path)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        for ddl in ("ALTER TABLE cases ADD COLUMN application_date TEXT", "ALTER TABLE cases ADD COLUMN ask_label TEXT",
                    "ALTER TABLE cases ADD COLUMN selected_json TEXT", "ALTER TABLE cases ADD COLUMN selection_touched INTEGER DEFAULT 0",
                    "ALTER TABLE documents ADD COLUMN pages_json TEXT", "ALTER TABLE documents ADD COLUMN text TEXT"):
            try:  # older demo databases
                self.conn.execute(ddl)
            except sqlite3.OperationalError:
                pass
        self.docs = DocStore(ttl_seconds=settings.doc_ttl_min * 60)

    # ---------------------------------------------------------------- helpers
    def _exec(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        row = self.conn.execute(sql, params).fetchone()
        return _row(row) if row else None

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        return [_row(r) for r in self.conn.execute(sql, params).fetchall()]

    def audit(self, actor: str, action: str, record: str, detail: dict | None = None) -> None:
        self._exec("INSERT INTO audit(at, actor, action, record, detail_json) VALUES (?,?,?,?,?)",
                   (now(), actor, action, record, json.dumps(detail or {})))

    # ---------------------------------------------------------------- cases
    def create_case(self, applicant_name: str, other_party_name: str | None, case_type: str | None, created_by: str,
                    work_type: str | None = None, safe_contact_method: str | None = None, safe_contact_value: str | None = None,
                    safe_times: str | None = None, firm_name: str | None = None, application_date: str | None = None,
                    ask_label: str | None = None) -> dict:
        cid = secrets.token_hex(8)
        ref = neutral_ref()
        self._exec(
            "INSERT INTO cases(id, ref, applicant_name, applicant_first_name, other_party_name, case_type, work_type, created_by, created_at,"
            " safe_contact_method, safe_contact_value, safe_times, firm_name, application_date, ask_label) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, ref, applicant_name, (applicant_name.split() or [""])[0], other_party_name, case_type, work_type, created_by, now(),
             safe_contact_method, safe_contact_value, safe_times, firm_name, application_date,
             ask_label if ask_label is not None else "Letter from your support worker"))
        self.audit(created_by, "case.create", cid, {"ref": ref})
        self.add_event(cid, "case_created", "Your case has been set up.", f"Case {ref} created.", created_by)
        return self.get_case(cid)

    def get_case(self, case_id: str) -> dict | None:
        return self._one("SELECT * FROM cases WHERE id=? OR ref=?", (case_id, case_id))

    def list_cases(self) -> list[dict]:
        return self._all("SELECT * FROM cases ORDER BY created_at DESC")

    def update_case(self, case_id: str, **fields) -> dict | None:
        allowed = {"applicant_name", "other_party_name", "case_type", "work_type", "status", "safe_contact_method", "safe_contact_value", "safe_times", "firm_name", "application_date", "ask_label"}
        cols = [k for k in fields if k in allowed]
        if cols:
            self._exec(f"UPDATE cases SET {', '.join(f'{c}=?' for c in cols)} WHERE id=?", (*[fields[c] for c in cols], case_id))
        if "applicant_name" in fields and fields["applicant_name"] is not None:
            self._exec("UPDATE cases SET applicant_first_name=? WHERE id=?", ((fields["applicant_name"].split() or [""])[0], case_id))
        return self.get_case(case_id)

    def set_selection(self, case_id: str, document_ids: list[str], actor: str) -> dict | None:
        """An empty selection means "back to the default" (the latest document that meets the requirements)."""
        self._exec("UPDATE cases SET selected_json=?, selection_touched=? WHERE id=?", (json.dumps(document_ids), 1 if document_ids else 0, case_id))
        self.audit(actor, "selection.set", case_id, {"document_ids": document_ids})
        return self.get_case(case_id)

    def latest_client_link(self, case_id: str) -> dict | None:
        link = self._one("SELECT * FROM client_links WHERE case_id=? AND revoked=0 ORDER BY created_at DESC LIMIT 1", (case_id,))
        return link if link and link["expires_at"] >= now() else None

    def latest_submission(self, case_id: str) -> dict | None:
        row = self._one("SELECT id FROM submissions WHERE case_id=? ORDER BY submitted_at DESC LIMIT 1", (case_id,))
        return self.get_submission(row["id"]) if row else None

    # ---------------------------------------------------------------- documents
    def add_document(self, case_id: str, filename: str, uploaded_by: str, claimed_para: str | None,
                     data: bytes | None, text: str | None, replaces: str | None = None, pages: list[dict] | None = None) -> dict:
        did = secrets.token_hex(8)
        version = 1
        if replaces:
            prev = self.get_document(replaces)
            version = (prev["version"] + 1) if prev else 1
        self._exec("INSERT INTO documents(id, case_id, filename, uploaded_by, uploaded_at, claimed_para, replaces_document_id, version, status, pages_json, text)"
                   " VALUES (?,?,?,?,?,?,?,?,?,?,?)", (did, case_id, filename, uploaded_by, now(), claimed_para, replaces, version, "checking",
                                                      json.dumps(pages) if pages else None, text))
        self.docs.put(did, data, text)
        self.audit(uploaded_by, "document.upload", did, {"case_id": case_id, "filename": filename, "version": version})
        who = "You" if uploaded_by == "client" else "Your solicitor"
        self.add_event(case_id, "document_received", f"{who} added a document. We are checking it now.",
                       f"Document {filename} (v{version}) uploaded by {uploaded_by}; check running.", uploaded_by)
        return self.get_document(did)

    def set_document_result(self, document_id: str, result: dict | None, error: str | None = None) -> None:
        if result is None:
            self._exec("UPDATE documents SET status='error', error=? WHERE id=?", (error, document_id))
            return
        result = {**result, "checked_at": now()}
        self._exec("UPDATE documents SET status='done', verdict=?, result_json=? WHERE id=?",
                   (result["verdict"], json.dumps(result, ensure_ascii=False), document_id))
        doc = self.get_document(document_id)
        self.add_event(doc["case_id"], "document_checked", result.get("client_message", "Your document has been checked."),
                       result.get("provider_summary", ""), "service")

    def get_document(self, document_id: str) -> dict | None:
        d = self._one("SELECT * FROM documents WHERE id=?", (document_id,))
        if d:
            d["result"] = json.loads(d.pop("result_json")) if d.get("result_json") else None
            d["pages"] = json.loads(d.pop("pages_json")) if d.get("pages_json") else None
            d["text_available"] = bool(d.get("text")) or self.docs.has(document_id)
        return d

    def document_text(self, document_id: str) -> str | None:
        """Extracted text: from memory if held (freshest after transcription), else the row, until purged."""
        item = self.docs.get(document_id)
        if item and item.text:
            return item.text
        row = self._one("SELECT text FROM documents WHERE id=? AND purged=0", (document_id,))
        return row["text"] if row and row.get("text") else None

    def set_document_text(self, document_id: str, text: str) -> None:
        self.docs.set_text(document_id, text)
        self._exec("UPDATE documents SET text=? WHERE id=?", (text, document_id))

    def list_documents(self, case_id: str, include_superseded: bool = True) -> list[dict]:
        docs = [self.get_document(r["id"]) for r in self._all("SELECT id FROM documents WHERE case_id=? ORDER BY uploaded_at", (case_id,))]
        if not include_superseded:
            replaced = {d["replaces_document_id"] for d in docs if d.get("replaces_document_id")}
            docs = [d for d in docs if d["id"] not in replaced]
        return docs

    def purge_case_documents(self, case_id: str, actor: str) -> int:
        n = 0
        for d in self.list_documents(case_id):
            if self.docs.drop(d["id"]):
                n += 1
            self._exec("UPDATE documents SET purged=1, text=NULL WHERE id=?", (d["id"],))
        self.audit(actor, "documents.purge", case_id, {"count": n})
        return n

    # ---------------------------------------------------------------- tracker, requests, links
    def add_event(self, case_id: str, event_type: str, applicant_text: str, solicitor_text: str, created_by: str, visible_to_applicant: bool = True) -> dict:
        eid = secrets.token_hex(6)
        self._exec("INSERT INTO tracker_events(id, case_id, event_type, applicant_text, solicitor_text, visible_to_applicant, created_by, created_at)"
                   " VALUES (?,?,?,?,?,?,?,?)", (eid, case_id, event_type, applicant_text, solicitor_text, int(visible_to_applicant), created_by, now()))
        return self._one("SELECT * FROM tracker_events WHERE id=?", (eid,))

    def list_events(self, case_id: str, applicant_view: bool = False) -> list[dict]:
        rows = self._all("SELECT * FROM tracker_events WHERE case_id=? ORDER BY created_at", (case_id,))
        if applicant_view:
            rows = [{"id": r["id"], "event_type": r["event_type"], "text": r["applicant_text"], "created_at": r["created_at"]}
                    for r in rows if r["visible_to_applicant"]]
        return rows

    def add_request(self, case_id: str, document_id: str, recipient: str | None, text: str, actor: str) -> dict:
        rid = secrets.token_hex(6)
        self._exec("INSERT INTO evidence_requests(id, case_id, document_id, recipient, drafted_text, status, created_at) VALUES (?,?,?,?,?,?,?)",
                   (rid, case_id, document_id, recipient, text, "drafted", now()))
        self.audit(actor, "request.draft", rid, {"case_id": case_id, "document_id": document_id})
        return self._one("SELECT * FROM evidence_requests WHERE id=?", (rid,))

    def mark_request_sent(self, request_id: str, actor: str) -> dict | None:
        self._exec("UPDATE evidence_requests SET status='sent', sent_at=? WHERE id=?", (now(), request_id))
        req = self._one("SELECT * FROM evidence_requests WHERE id=?", (request_id,))
        if req:
            self.add_event(req["case_id"], "request_sent", "Your solicitor has asked for an updated letter.",
                           f"Request sent to {req['recipient'] or 'the author'}.", actor)
            self.audit(actor, "request.sent", request_id)
        return req

    def list_requests(self, case_id: str) -> list[dict]:
        return self._all("SELECT * FROM evidence_requests WHERE case_id=? ORDER BY created_at", (case_id,))

    def create_client_link(self, case_id: str, days: int = 7) -> dict:
        token = secrets.token_urlsafe(16)
        exp = datetime.fromtimestamp(time.time() + days * 86400, tz=timezone.utc).isoformat(timespec="seconds")
        self._exec("INSERT INTO client_links(token, case_id, created_at, expires_at) VALUES (?,?,?,?)", (token, case_id, now(), exp))
        return {"token": token, "case_id": case_id, "expires_at": exp}

    def resolve_client_link(self, token: str) -> dict | None:
        link = self._one("SELECT * FROM client_links WHERE token=? AND revoked=0", (token,))
        if not link or link["expires_at"] < now():
            return None
        return link

    def revoke_client_links(self, case_id: str) -> None:
        self._exec("UPDATE client_links SET revoked=1 WHERE case_id=?", (case_id,))

    # ---------------------------------------------------------------- submissions (link 2)
    def create_submission(self, case_id: str, document_ids: list[str], notes: str | None, submit_anyway_reason: str | None,
                          actor: str, resubmission_of: str | None = None) -> dict:
        case = self.get_case(case_id)
        docs = [self.get_document(d) for d in document_ids]
        docs = [d for d in docs if d and d["case_id"] == case_id and d["result"]]
        snapshot = {"application": {"applicant_name": case["applicant_name"], "other_party_name": case["other_party_name"], "case_type": case["case_type"], "application_date": case.get("application_date")},
                    "documents": [{"document_id": d["id"], "filename": d["filename"], "version": d["version"], "claimed_para": d["claimed_para"],
                                   "result": d["result"]} for d in docs],
                    "rules_version": docs[0]["result"].get("rules_version") if docs else None, "frozen_at": now()}
        verdicts = [d["result"]["verdict"] for d in docs]
        case_verdict = "meets" if "meets" in verdicts else "needs_caseworker" if "needs_caseworker" in verdicts else "needs_change" if "needs_change" in verdicts else "no_evidence_yet"
        sid = secrets.token_hex(8)
        prev = self._one("SELECT laa_ref FROM submissions WHERE id=?", (resubmission_of,)) if resubmission_of else None
        laa_ref = prev["laa_ref"] if prev else f"L{secrets.randbelow(900000) + 100000}"
        self._exec("INSERT INTO submissions(id, case_id, laa_ref, firm_name, submitted_at, document_ids_json, snapshot_json, notes, submit_anyway_reason,"
                   " case_verdict, status, resubmission_of) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (sid, case_id, laa_ref, case["firm_name"], now(), json.dumps([d["id"] for d in docs]), json.dumps(snapshot, ensure_ascii=False),
                    notes, submit_anyway_reason, case_verdict, "submitted", resubmission_of))
        self.audit(actor, "submission.create", sid, {"case_id": case_id, "laa_ref": laa_ref, "documents": [d["id"] for d in docs], "submit_anyway": bool(submit_anyway_reason)})
        self.add_event(case_id, "submitted", "Your application has been sent to the Legal Aid Agency.", f"Submitted to the LAA as {laa_ref}.", actor)
        return self.get_submission(sid)

    def set_laa_check(self, submission_id: str, laa_check: dict, differences: list[dict]) -> None:
        self._exec("UPDATE submissions SET laa_check_json=?, differences_json=? WHERE id=?",
                   (json.dumps(laa_check, ensure_ascii=False), json.dumps(differences, ensure_ascii=False), submission_id))

    def get_submission(self, submission_id: str) -> dict | None:
        s = self._one("SELECT * FROM submissions WHERE id=? OR laa_ref=?", (submission_id, submission_id))
        if not s:
            return None
        s["document_ids"] = json.loads(s.pop("document_ids_json") or "[]")
        s["snapshot"] = json.loads(s.pop("snapshot_json") or "{}")
        s["laa_check"] = json.loads(s.pop("laa_check_json")) if s.get("laa_check_json") else None
        s["differences"] = json.loads(s.pop("differences_json")) if s.get("differences_json") else []
        s["decisions"] = self._all("SELECT * FROM decisions WHERE submission_id=? ORDER BY created_at", (submission_id,))
        return s

    def list_submissions(self) -> list[dict]:
        order = {"meets": 0, "needs_caseworker": 1, "needs_change": 2, "no_evidence_yet": 3}
        subs = [self.get_submission(r["id"]) for r in self._all("SELECT id FROM submissions ORDER BY submitted_at")]
        subs.sort(key=lambda s: (0 if s["status"] == "submitted" else 1, order.get(s["case_verdict"], 9), s["submitted_at"]))
        return subs

    def add_decision(self, submission_id: str, caseworker: str, action: str, note: str | None) -> dict:
        sub = self.get_submission(submission_id)
        tool = sub["case_verdict"]
        agreed = (action == "accept" and tool == "meets") or (action == "return" and tool == "needs_change") or (action == "refer" and tool == "needs_caseworker")
        did = secrets.token_hex(6)
        self._exec("INSERT INTO decisions(id, submission_id, caseworker, action, note, agreed_with_tool, tool_verdict, created_at) VALUES (?,?,?,?,?,?,?,?)",
                   (did, submission_id, caseworker, action, note, int(agreed), tool, now()))
        status = {"accept": "accepted", "return": "returned", "refer": "referred"}.get(action, action)
        self._exec("UPDATE submissions SET status=? WHERE id=?", (status, submission_id))
        self.audit(caseworker, f"decision.{action}", submission_id, {"agreed_with_tool": agreed})
        prompt = {"accepted": "A decision has been made. Your solicitor will be in touch.",
                  "returned": "The Legal Aid Agency needs one more thing. Your solicitor is dealing with it.",
                  "referred": "Your application is being looked at. Your solicitor will be in touch."}[status]
        # LAA events never reach the applicant automatically: hidden until the solicitor releases it
        self.add_event(sub["case_id"], f"laa_{status}", prompt, f"LAA {status} submission {sub['laa_ref']}." + (f" Note: {note}" if note else ""), caseworker, visible_to_applicant=False)
        return self._one("SELECT * FROM decisions WHERE id=?", (did,))

    def release_event(self, event_id: str, actor: str, applicant_text: str | None = None) -> dict | None:
        if applicant_text:
            self._exec("UPDATE tracker_events SET visible_to_applicant=1, applicant_text=? WHERE id=?", (applicant_text, event_id))
        else:
            self._exec("UPDATE tracker_events SET visible_to_applicant=1 WHERE id=?", (event_id,))
        self.audit(actor, "event.release", event_id)
        return self._one("SELECT * FROM tracker_events WHERE id=?", (event_id,))

    def list_audit(self, record: str | None = None) -> list[dict]:
        if record:
            return self._all("SELECT * FROM audit WHERE record=? ORDER BY id", (record,))
        return self._all("SELECT * FROM audit ORDER BY id DESC LIMIT 500")


def _row(r: sqlite3.Row) -> dict:
    return {k: r[k] for k in r.keys()}


@dataclass
class _Doc:
    data: bytes | None
    text: str | None
    expires_at: float
    files: list | None = None  # [(bytes, media_type)] per page, for the file links


class DocStore:
    """Document bytes and text in memory only, dropped after the TTL."""

    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._items: dict[str, _Doc] = {}
        self._lock = threading.Lock()

    def put(self, doc_id: str, data: bytes | None, text: str | None) -> None:
        with self._lock:
            self._items[doc_id] = _Doc(data, text, time.time() + self.ttl)

    def get(self, doc_id: str) -> _Doc | None:
        self.sweep()
        return self._items.get(doc_id)

    def has(self, doc_id: str) -> bool:
        return self.get(doc_id) is not None

    def set_text(self, doc_id: str, text: str) -> None:
        with self._lock:
            if doc_id in self._items:
                self._items[doc_id].text = text

    def drop(self, doc_id: str) -> bool:
        with self._lock:
            return self._items.pop(doc_id, None) is not None

    def sweep(self) -> None:
        t = time.time()
        with self._lock:
            for k in [k for k, v in self._items.items() if v.expires_at < t]:
                del self._items[k]
