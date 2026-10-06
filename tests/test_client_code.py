"""The client's link token doubles as a short code they can type on the start screen."""
import os
import re
import tempfile

from app.store import Store, normalise_client_code


def _store_with_case():
    store = Store(os.path.join(tempfile.mkdtemp(), "t.sqlite3"))
    case = store.create_case("Jane Doe", "John Doe", "Child arrangements", "provider", firm_name="Hartley & Webb Solicitors")
    return store, case


def test_new_links_are_eight_unambiguous_characters():
    store, case = _store_with_case()
    token = store.create_client_link(case["id"], 7)["token"]
    assert re.fullmatch(r"[A-HJKMNP-Z2-9]{8}", token), token


def test_a_typed_code_resolves_whatever_its_case_spacing_or_hyphen():
    store, case = _store_with_case()
    token = store.create_client_link(case["id"], 7)["token"]
    for typed in (token, token.lower(), f"{token[:4]}-{token[4:]}", f" {token[:4]} {token[4:]} "):
        link = store.resolve_client_link(typed)
        assert link and link["case_id"] == case["id"], typed


def test_unknown_and_revoked_codes_do_not_resolve():
    store, case = _store_with_case()
    token = store.create_client_link(case["id"], 7)["token"]
    assert store.resolve_client_link("ZZZZ-ZZZZ") is None
    store.revoke_client_links(case["id"])
    assert store.resolve_client_link(token) is None


def test_normalise():
    assert normalise_client_code("k7qm-4xpr ") == "K7QM4XPR"
