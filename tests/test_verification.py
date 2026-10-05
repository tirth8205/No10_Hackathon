"""Verification checks on the author and organisation (engine/verification.py).

Offline and deterministic: the module's two HTTP helpers are monkeypatched so no network is
used. One live test at the end talks to postcodes.io and is skipped when there is no network.
"""
import asyncio
import json
import re
import socket
import time
from pathlib import Path

import pytest

from engine import verification as v
from engine.models import Classification, Parties
from engine.pipeline import rule_for_paragraph
from engine.rules import load_rules

ROOT = Path(__file__).resolve().parent.parent
RULES = load_rules()
GOLD = {c["id"]: c for c in json.load(open(ROOT / "data" / "moj_gold_cases.json"))["cases"]}


# --------------------------------------------------------------------------- helpers
def cls(**kw) -> Classification:
    base = dict(rule_id="x", confidence="high", document_kind="letter", language="en", rationale="")
    base.update(kw)
    return Classification(**base)


def run(text, para, *, author_org=None, document_kind="letter", timeout=4.0):
    rule = rule_for_paragraph(RULES, para) if para else None
    return asyncio.run(v.verify_document(text, cls(author_org=author_org, document_kind=document_kind), Parties(), rule, timeout=timeout))


def by_id(checks, check_id):
    hits = [c for c in checks if c.id == check_id]
    return hits[0] if hits else None


POSTCODES = {  # (admin_district, pfa) exactly as postcodes.io returns them
    "LS1 4AP": ("Leeds", "West Yorkshire"),
    "S1 2HH": ("Sheffield", "South Yorkshire"),
    "BA1 1JQ": ("Bath and North East Somerset", "Avon and Somerset"),
    "SW1A 2AA": ("Westminster", "Metropolitan Police"),
    "PL1 2AA": ("Plymouth", "Devon & Cornwall"),
    "HR1 2AA": ("Herefordshire, County of", "West Mercia"),
    "EH1 1YZ": ("City of Edinburgh", "Scotland"),
    "BT1 5GS": ("Belfast", None),
}


@pytest.fixture
def offline(monkeypatch):
    """Fake postcodes.io and fake websites; records every URL requested."""
    calls = {"json": [], "text": [], "headers": []}

    async def fake_json(url, *, timeout, headers=None):
        calls["json"].append(url)
        calls["headers"].append(headers or {})
        pc = url.rsplit("/", 1)[1].replace("%20", " ")
        if pc in POSTCODES:
            district, pfa = POSTCODES[pc]
            return {"status": 200, "result": {"postcode": pc, "admin_district": district, "pfa": pfa}}
        return {"status": 404, "error": "Postcode not found"}

    async def fake_text(url, *, timeout, max_bytes=v.MAX_PAGE_BYTES):
        calls["text"].append(url)
        if "northgate" in url:
            return v.Fetched(200, "<html><head><title>Home</title><style>a{}</style></head><body>Welcome to the Northgate Domestic Abuse Service website</body></html>")
        if "nowhere" in url:
            return v.Fetched(None, "", "the domain name does not resolve")
        if "blocked" in url:
            return v.Fetched(403, "<html>Forbidden</html>")
        return v.Fetched(200, "<html><body>A page about something else entirely</body></html>")

    monkeypatch.setattr(v, "_http_get_json", fake_json)
    monkeypatch.setattr(v, "_http_get_text", fake_text)
    monkeypatch.delenv("CHARITY_COMMISSION_API_KEY", raising=False)
    return calls


# --------------------------------------------------------------------------- letters in the style of the generator
P1_POLICE_EMAIL = """From: DC Emma Reid <reid.4821@westyorkshire.pnn.police.uk>
To: Hartley & Moss Solicitors <family@hartleymoss.co.uk>
Date: 3 September 2026
Subject: RE: Sarah Okafor – crime reference AB/12345/26

Good afternoon,

I can confirm that Daniel Hughes (date of birth 4 May 1988) was arrested on 10 August 2026 on suspicion of assault occasioning actual bodily harm (section 47 Offences Against the Person Act 1861). The victim in this matter is Sarah Okafor, his former partner. Daniel was interviewed and has been released on conditional bail until 14 October 2026 while enquiries continue.

Kind regards,
DC Emma Reid
Safeguarding and Domestic Abuse Investigation Team
West Yorkshire Police
Elland Road, Leeds LS1 4AP
"""

P11_GMAIL = """From: Hannah Fletcher <fletcherdoctor@gmail.com>
Date: 1 September 2026
Subject: Letter for Sarah Okafor

I understand that Sarah Okafor wishes to access legal aid for a family dispute as a victim of domestic abuse.

I examined Sarah Okafor in person on 25 August 2026. In my reasonable professional judgement, she has injuries consistent with being a victim of domestic abuse.

Hannah Fletcher"""

P11_GP = """1 September 2026

To whom it may concern

Re: Sarah Okafor, date of birth 3 March 1990

I am a general practitioner registered with the General Medical Council (GMC number 7106698). I examined Sarah Okafor in person on 25 August 2026. In my reasonable professional judgement, she has injuries consistent with being a victim of domestic abuse.

Dr Hannah Fletcher
Riverside Medical Centre
"""

P17_SUPPORT_ORG = """Northgate Domestic Abuse Service
Registered charity number 1122334
www.northgate-das.org.uk

I understand that Sarah Okafor wishes to access legal aid for a family dispute as a victim of domestic abuse.

I can confirm that our organisation is situated in the United Kingdom and has been operating for an uninterrupted period of six months or more.

Aisha Patel
Senior Outreach Worker
Northgate Domestic Abuse Service
"""

DAPN = """DOMESTIC ABUSE PROTECTION NOTICE
Section 22 Domestic Abuse Act 2021

Given by: Greater Manchester Police
Date and time given: 20 August 2026 at 23:05
Person to whom this notice is given: Daniel Hughes
Person to be protected: Sarah Okafor

An application for a Domestic Abuse Protection Order will be made to Manchester Magistrates' Court within 48 hours.

Authorising officer: Superintendent Grace Mensah"""

CAUTION_NON_DA = """WEST YORKSHIRE POLICE
RECORD OF SIMPLE CAUTION

Name of person cautioned: Daniel Hughes
Offence: possession of a controlled drug (section 5 Misuse of Drugs Act 1971)
Date of offence: 1 July 2026
Victim: N/A – no individual victim
Administering officer: PS Grace Mensah"""

MARAC = """Bath and Northeast Somerset Council – Multi-Agency Risk Assessment Conference (MARAC)
Guildhall, High Street, Bath BA1 1JQ

I am the MARAC Coordinator for Bath and Northeast Somerset Council and a member of the MARAC."""


# --------------------------------------------------------------------------- 1. official_domain
def test_official_domain_pnn_police_passes(offline):
    c = by_id(run(P1_POLICE_EMAIL, "1", author_org="West Yorkshire Police"), "official_domain")
    assert c.status == "pass"
    assert "westyorkshire.pnn.police.uk" in c.detail
    assert "verified" not in c.detail.lower()  # a domain shows the organisation type, not the person


@pytest.mark.parametrize("domain", ["nhs.net", "leedsth.nhs.uk", "bathnes.gov.uk", "cafcass.gov.uk", "solicitor.cjsm.net", "met.police.uk"])
def test_official_domain_list(offline, domain):
    c = by_id(run(f"From: Someone <a.person@{domain}>\n\nLetter body.", "19", author_org="Org", document_kind="email"), "official_domain")
    assert c.status == "pass" and domain in c.detail


def test_official_domain_webmail_warns(offline):
    c = by_id(run(P11_GMAIL, "11", document_kind="email"), "official_domain")
    assert c.status == "warn"
    assert "gmail.com" in c.detail and "personal" in c.detail


def test_official_domain_other_domain_is_unknown_with_link(offline):
    text = "From: Hartley & Moss Solicitors <family@hartleymoss.co.uk>\nTo: Legal Aid Agency\n\nI write to confirm..."
    c = by_id(run(text, "1", author_org="Hartley & Moss Solicitors", document_kind="email"), "official_domain")
    assert c.status == "unknown" and "hartleymoss.co.uk" in c.detail and c.link == "https://hartleymoss.co.uk/"


def test_official_domain_prefers_from_line_over_to_line(offline):
    text = "From: Dr X <drx@hotmail.com>\nTo: Police <a@westyorkshire.pnn.police.uk>\n\nbody"
    c = by_id(run(text, "11", document_kind="email"), "official_domain")
    assert c.status == "warn" and "hotmail.com" in c.detail


def test_official_domain_absent(offline):
    # an email with no visible address: unknown; a plain letter with no address: check not shown at all
    assert by_id(run("Dear Sir, body with no address.", "11", document_kind="email"), "official_domain").status == "unknown"
    assert by_id(run(GOLD["MOJ-P17-accepted-01"]["documents"][0]["text"], "17"), "official_domain") is None


# --------------------------------------------------------------------------- 2. website_reachable
def test_website_pass_when_org_named_on_page(offline):
    c = by_id(run(P17_SUPPORT_ORG, "17", author_org="Northgate Domestic Abuse Service"), "website_reachable")
    assert c.status == "pass" and c.link == "https://www.northgate-das.org.uk"
    assert offline["text"] == ["https://www.northgate-das.org.uk"]


def test_website_warn_when_org_absent_or_blocked(offline):
    text = P17_SUPPORT_ORG.replace("www.northgate-das.org.uk", "https://www.other-site.org/about")
    c = by_id(run(text, "17", author_org="Northgate Domestic Abuse Service"), "website_reachable")
    assert c.status == "warn" and "does not mention Northgate Domestic Abuse Service" in c.detail
    text = P17_SUPPORT_ORG.replace("www.northgate-das.org.uk", "https://blocked.example.org/")
    c = by_id(run(text, "17", author_org="Northgate Domestic Abuse Service"), "website_reachable")
    assert c.status == "warn" and "HTTP 403" in c.detail


def test_website_fail_when_unreachable(offline):
    text = P17_SUPPORT_ORG.replace("www.northgate-das.org.uk", "https://nowhere.example.invalid/")
    c = by_id(run(text, "17", author_org="Northgate Domestic Abuse Service"), "website_reachable")
    assert c.status == "fail" and "could not be reached" in c.detail and c.link == "https://nowhere.example.invalid/"


def test_website_unknown_without_org_and_skips_govuk(offline):
    text = P17_SUPPORT_ORG.replace("www.northgate-das.org.uk", "https://www.northgate-das.org.uk")
    c = by_id(run(text, "17", author_org=None), "website_reachable")
    assert c.status == "unknown"
    # the MoJ letters only link to gov.uk guidance: no website check, nothing fetched
    offline["text"].clear()
    checks = run(GOLD["MOJ-P19-accepted-01"]["documents"][0]["text"], "19", author_org="Bath and Northeast Somerset Council")
    assert by_id(checks, "website_reachable") is None and offline["text"] == []


def test_website_reads_at_most_three_urls(offline):
    text = "\n".join(f"https://site{i}.example.org/" for i in range(6))
    checks = run(text, "17", author_org="Org")
    assert len([c for c in checks if c.id == "website_reachable"]) == 3


# --------------------------------------------------------------------------- 3. postcode_area
def test_postcode_force_match_passes(offline):
    c = by_id(run(P1_POLICE_EMAIL, "1", author_org="West Yorkshire Police"), "postcode_area")
    assert c.status == "pass"
    assert "LS1 4AP is in Leeds; police force area West Yorkshire Police" in c.detail
    assert c.link == v.LINK_POLICE_AREA
    assert offline["json"] == [v.POSTCODES_API.format(postcode="LS1%204AP")]


def test_postcode_force_mismatch_fails(offline):
    text = P1_POLICE_EMAIL.replace("West Yorkshire Police", "South Yorkshire Police")
    c = by_id(run(text, "1", author_org="South Yorkshire Police"), "postcode_area")
    assert c.status == "fail"
    assert "letter is from South Yorkshire Police but the address is in the West Yorkshire Police area" in c.detail


def test_postcode_force_name_variants(offline):
    text = "Avon & Somerset Constabulary\nBath BA1 1JQ"
    assert by_id(run(text, "1"), "postcode_area").status == "pass"
    text = "Metropolitan Police Service\nLondon SW1A 2AA"
    assert by_id(run(text, "1"), "postcode_area").status == "pass"
    text = "Devon and Cornwall Police\nPlymouth PL1 2AA"
    assert by_id(run(text, "1"), "postcode_area").status == "pass"
    c = by_id(run("Police Scotland\nEdinburgh EH1 1YZ", "1"), "postcode_area")
    assert c.status == "pass" and "police force area Police Scotland" in c.detail and "Scotland Police" not in c.detail
    c = by_id(run("Police Service of Northern Ireland\nBelfast BT1 5GS", "1"), "postcode_area")
    assert c.status == "unknown" and "No police force area is recorded" in c.detail  # postcodes.io has no pfa for NI
    c = by_id(run("West Mercia Police\nHereford HR1 2AA", "1"), "postcode_area")
    assert c.status == "pass" and "HR1 2AA is in Herefordshire;" in c.detail


def test_force_normaliser_handles_national_and_renamed_forces():
    assert v._forces_match("Police Service of Northern Ireland", "Northern Ireland")
    assert v._forces_match("PSNI", "Northern Ireland") is False  # the display name is compared, never the abbreviation
    assert v._forces_match("Police Scotland", "Scotland")
    assert v._forces_match("Metropolitan Police Service", "Metropolitan Police")
    assert v._forces_match("Avon and Somerset Constabulary", "Avon and Somerset")
    assert v._forces_match("Hampshire and Isle of Wight Constabulary", "Hampshire")  # renamed in 2023; postcodes.io still says Hampshire
    assert v._forces_match("City of London Police", "City of London")
    for a, b in [("West Yorkshire Police", "South Yorkshire"), ("North Wales Police", "South Wales"), ("Essex Police", "Sussex"),
                 ("Surrey Police", "Sussex"), ("Police Scotland", "Metropolitan Police"), ("Metropolitan Police Service", "City of London")]:
        assert not v._forces_match(a, b), (a, b)
    assert v._force_display("Scotland") == "Police Scotland"
    assert v._force_display("West Yorkshire") == "West Yorkshire Police"
    assert v._force_display("Metropolitan Police") == "Metropolitan Police"
    assert v._find_force("the Police Service of Scotland").display == "Police Scotland"
    assert v._find_force("PSNI").display == "Police Service of Northern Ireland"
    assert v._find_force("the Met").display == "Metropolitan Police Service"


def test_postcode_force_only_compared_when_author_is_the_police(offline):
    # a solicitor's email names the force but the postcode is the solicitor's own: never a 'fail' against the force
    text = ("From: Hartley & Moss Solicitors <family@hartleymoss.co.uk>\n\nI have spoken to West Yorkshire Police today and they "
            "confirmed the arrest.\n\nHartley & Moss Solicitors, 4 Mill Lane, Sheffield S1 2HH")
    c = by_id(run(text, "1", author_org="Hartley & Moss Solicitors", document_kind="email"), "postcode_area")
    assert c.status == "pass" and "also names Sheffield" in c.detail and "letter is from" not in c.detail
    # MARAC minutes from a council that mention the local force: compared with the council, not the force
    text = MARAC + "\nAttended by Avon and Somerset Constabulary and the IDVA service."
    c = by_id(run(text.replace("BA1 1JQ", "LS1 4AP"), "13", author_org="Bath and Northeast Somerset Council"), "postcode_area")
    assert c.status == "warn" and "Bath and Northeast Somerset Council" in c.detail
    # the police themselves, or no classified organisation: the force comparison still applies
    c = by_id(run(P1_POLICE_EMAIL.replace("Leeds LS1 4AP", "Sheffield S1 2HH"), "1", author_org="West Yorkshire Police"), "postcode_area")
    assert c.status == "fail"
    assert by_id(run("West Yorkshire Police\nS1 2HH", "1", author_org=None), "postcode_area").status == "fail"


def test_postcode_council_match_and_mismatch(offline):
    assert by_id(run(MARAC, "13", author_org="Bath and Northeast Somerset Council"), "postcode_area").status == "pass"
    c = by_id(run(MARAC.replace("BA1 1JQ", "LS1 4AP"), "13", author_org="Bath and Northeast Somerset Council"), "postcode_area")
    assert c.status == "warn" and "Bath and Northeast Somerset Council" in c.detail and c.link == v.LINK_FIND_COUNCIL


def test_postcode_nothing_to_compare_is_unknown_and_town_named_passes(offline):
    c = by_id(run("Kingsway Surgery\n12 Mill Lane\nS1 2HH", "11"), "postcode_area")
    assert c.status == "unknown" and "S1 2HH is in Sheffield" in c.detail
    c = by_id(run("Kingsway Surgery\n12 Mill Lane, Sheffield\nS1 2HH", "11"), "postcode_area")
    assert c.status == "pass" and "also names Sheffield" in c.detail


def test_postcode_not_found_warns_and_lookup_failure_is_unknown(offline, monkeypatch):
    c = by_id(run("Kingsway Surgery\nZZ9 9ZZ", "11"), "postcode_area")
    assert c.status == "warn" and "not a recognised UK postcode" in c.detail

    async def down(url, *, timeout, headers=None):
        return None

    monkeypatch.setattr(v, "_http_get_json", down)
    c = by_id(run("Kingsway Surgery\nLS1 4AP", "11"), "postcode_area")
    assert c.status == "unknown" and "could not run" in c.detail


def test_postcode_absent_means_no_check(offline):
    assert by_id(run(P11_GP, "11"), "postcode_area") is None
    assert offline["json"] == []


def test_postcode_regex_ignores_reference_numbers():
    assert v._find_postcodes("Custody record: AB/12345/26, case LE48P12345, GMC number 7106698, PIN 45C1234E, section 47") == []
    assert v._find_postcodes("Leeds LS1 4AP and London SW1A2AA") == ["LS1 4AP", "SW1A 2AA"]


# --------------------------------------------------------------------------- 4. registration
def test_registration_gmc_format_and_link(offline):
    c = by_id(run(P11_GP, "11", author_org="Riverside Medical Centre"), "registration")
    assert c.status == "unknown"
    assert c.detail == "GMC number 7106698 has the right format; verify on the register."
    assert c.link == "https://www.gmc-uk.org/registrants/7106698"


def test_registration_nmc_hcpc_swe_gdc(offline):
    c = by_id(run("I am a health visitor registered with the Nursing and Midwifery Council (PIN 45C1234E).", "11"), "registration")
    assert c.status == "unknown" and "NMC PIN 45C1234E" in c.detail and c.link == v.LINK_NMC
    c = by_id(run("Paramedic, HCPC registration PA12345.", "11"), "registration")
    assert c.status == "unknown" and "PA12345" in c.detail and c.link == v.LINK_HCPC
    c = by_id(run("Family Court Adviser, registered with Social Work England (SW12345).", "10"), "registration")
    assert c.status == "unknown" and "SW12345" in c.detail and c.link == v.LINK_SWE
    c = by_id(run("Dentist, GDC number 123456.", "11"), "registration")
    assert c.status == "unknown" and "GDC number 123456" in c.detail and c.link == v.LINK_GDC


def test_registration_wrong_format_warns(offline):
    c = by_id(run("Dr A. Smith, GMC number 71066.", "11"), "registration")
    assert c.status == "warn" and "71066" in c.detail and "7 digits" in c.detail


def test_registration_para11_without_number_or_profession_warns(offline):
    for case in ("MOJ-P11-accepted-01", "MOJ-P11-rejected-02"):
        c = by_id(run(GOLD[case]["documents"][0]["text"], "11"), "registration")
        assert c.status == "warn" and "the LAA may ask for it" in c.detail
    c = by_id(run(P11_GMAIL, "11", document_kind="email"), "registration")
    assert c.status == "warn"


def test_registration_omitted_when_profession_named_without_number(offline):
    text = P11_GP.replace(" registered with the General Medical Council (GMC number 7106698)", "")
    assert by_id(run(text, "11"), "registration") is None


def test_registration_body_named_without_number_warns_on_para11(offline):
    text = "I am GMC registered. I examined her on 12 September 2026 and she has had 11 years of symptoms."
    c = by_id(run(text, "11"), "registration")
    assert c.status == "warn" and "no registration number" in c.detail


def test_registration_not_run_for_unrelated_letters(offline):
    assert by_id(run(GOLD["MOJ-P17-accepted-01"]["documents"][0]["text"], "17"), "registration") is None


# --------------------------------------------------------------------------- 5. charity_register
def test_charity_builtin_match_passes(offline):
    checks = run(GOLD["MOJ-P18-accepted-01"]["documents"][0]["text"], "18", author_org="Women's Aid Federation of England")
    c = by_id(checks, "charity_register")
    assert c.status == "pass" and "1054154" in c.detail and "Local Women's Aid groups are separate" in c.detail
    assert "built-in list" in c.detail and "not from a live lookup" in c.detail and "verified" not in c.detail.lower()
    assert c.link.startswith("https://register-of-charities.charitycommission.gov.uk/en/charity-search?q=")
    assert offline["json"] == []  # no API call without a key
    c = by_id(run("Refuge\n\nWe supported her.", "17", author_org="Refuge"), "charity_register")
    assert c.status == "pass" and "277424" in c.detail


def test_charity_shared_name_is_unknown_not_pass(offline):
    # "Women's Aid" on its own is also what dozens of independent local charities call themselves (the MoJ P18 sample
    # letter is signed just "Women's Aid"), so a bare name match gives the national number as context but no pass
    c = by_id(run(GOLD["MOJ-P18-accepted-01"]["documents"][0]["text"], "18", author_org="Women’s Aid"), "charity_register")
    assert c.status == "unknown" and "1054154" in c.detail and "local" in c.detail and "Check the letterhead" in c.detail
    c = by_id(run("Rape Crisis\n\nWe supported her.", "15", author_org="Rape Crisis"), "charity_register")
    assert c.status == "unknown" and "1155140" in c.detail
    c = by_id(run("Rape Crisis England & Wales\n\nWe supported her.", "15", author_org="Rape Crisis England & Wales"), "charity_register")
    assert c.status == "pass" and "1155140" in c.detail


def test_builtin_charity_numbers_are_the_confirmed_ones():
    # each number was read from the charity's own website footer during review on 2026-10-05
    confirmed = {"Women's Aid Federation of England": "1054154", "Refuge": "277424", "Rape Crisis England & Wales": "1155140",
                 "Victim Support": "298028", "Respect": "1141636", "Welsh Women's Aid": "1140962", "Surviving Economic Abuse": "1173256",
                 "ManKind Initiative": "1089547", "Galop": "1077384", "Scottish Women's Aid": "SC001099"}
    assert {c["name"]: c["number"] for c in v.KNOWN_CHARITIES} == confirmed
    for c in v.KNOWN_CHARITIES:
        assert set(c.get("shared", ())) <= set(c["aliases"])


def test_charity_local_group_does_not_borrow_the_national_number(offline):
    c = by_id(run("Leeds Women's Aid\n\nWe supported her.", "17", author_org="Leeds Women's Aid"), "charity_register")
    assert c.status == "unknown" and "1054154" not in c.detail
    assert c.link == v.LINK_CHARITY_SEARCH.format(q="Leeds%20Women%27s%20Aid")


def test_charity_unknown_for_unlisted_org_with_quoted_number(offline):
    c = by_id(run(P17_SUPPORT_ORG, "17", author_org="Northgate Domestic Abuse Service"), "charity_register")
    assert c.status == "unknown"
    assert "Not found in the built-in list" in c.detail and "1122334" in c.detail
    assert c.link == v.LINK_CHARITY_SEARCH.format(q="1122334")


def test_charity_quoted_number_contradicting_builtin_warns(offline):
    text = P17_SUPPORT_ORG.replace("Northgate Domestic Abuse Service", "Refuge")
    c = by_id(run(text, "17", author_org="Refuge"), "charity_register")
    assert c.status == "warn" and "277424" in c.detail and "1122334" in c.detail


def test_charity_scottish_links_to_oscr(offline):
    c = by_id(run("Scottish Women's Aid\nEdinburgh", "17", author_org="Scottish Women's Aid"), "charity_register")
    assert c.status == "pass" and "SC001099" in c.detail and c.link == v.LINK_OSCR
    c = by_id(run("Glen Support, Scotland", "17", author_org="Glen Support"), "charity_register")
    assert c.status == "unknown" and v.LINK_OSCR in c.detail


def test_charity_skipped_for_public_bodies_and_other_paragraphs(offline):
    assert by_id(run(MARAC, "13", author_org="Bath and Northeast Somerset Council"), "charity_register") is None
    assert by_id(run(P11_GP, "11", author_org="Riverside Medical Centre"), "charity_register") is None
    assert by_id(run(P17_SUPPORT_ORG, "19", author_org="Northgate Domestic Abuse Service"), "charity_register") is None


def test_charity_api_used_when_key_is_set(offline, monkeypatch):
    monkeypatch.setenv("CHARITY_COMMISSION_API_KEY", "test-key")
    rows = [{"reg_charity_number": 1122334, "charity_name": "NORTHGATE DOMESTIC ABUSE SERVICE", "reg_status": "R"}]

    async def fake_api(url, *, timeout, headers=None):
        offline["json"].append(url)
        offline["headers"].append(headers or {})
        return rows

    monkeypatch.setattr(v, "_http_get_json", fake_api)
    text = P17_SUPPORT_ORG.replace("www.northgate-das.org.uk", "")
    c = by_id(run(text, "17", author_org="Northgate Domestic Abuse Service"), "charity_register")
    assert c.status == "pass" and "1122334" in c.detail
    assert offline["json"][0].startswith(v.CHARITY_API.format(name="")) and offline["headers"][0] == {"Ocp-Apim-Subscription-Key": "test-key"}

    rows.clear()
    c = by_id(run(text, "17", author_org="Northgate Domestic Abuse Service"), "charity_register")
    assert c.status == "unknown" and "No charity called" in c.detail


# --------------------------------------------------------------------------- 6. dapn_pilot
def test_dapn_pilot_force_passes(offline):
    c = by_id(run(DAPN, "6A", author_org="Greater Manchester Police"), "dapn_pilot")
    assert c.status == "pass" and "Greater Manchester Police" in c.detail and c.link == v.LINK_DAPN


def test_dapn_non_pilot_force_fails(offline):
    text = DAPN.replace("Greater Manchester Police", "West Yorkshire Police").replace("Manchester Magistrates", "Leeds Magistrates")
    c = by_id(run(text, "6A", author_org="West Yorkshire Police"), "dapn_pilot")
    assert c.status == "fail" and "West Yorkshire Police" in c.detail and "not in the DAPN pilot" in c.detail


def test_dapn_met_needs_a_pilot_borough(offline):
    text = DAPN.replace("Greater Manchester Police", "Metropolitan Police Service").replace("Manchester Magistrates", "Croydon Magistrates")
    assert by_id(run(text, "6A"), "dapn_pilot").status == "pass"
    text = DAPN.replace("Greater Manchester Police", "Metropolitan Police Service").replace("Manchester Magistrates", "Hackney Magistrates")
    assert by_id(run(text, "6A"), "dapn_pilot").status == "warn"


def test_dapn_no_force_is_unknown_and_other_paragraphs_omit(offline):
    assert by_id(run(DAPN.replace("Given by: Greater Manchester Police\n", ""), "6A"), "dapn_pilot").status == "unknown"
    assert by_id(run(DAPN.replace("ABUSE PROTECTION", "VIOLENCE PROTECTION"), "6"), "dapn_pilot") is None


# --------------------------------------------------------------------------- 7. offence_listed
def test_offence_listed_pass(offline):
    c = by_id(run(P1_POLICE_EMAIL, "1", author_org="West Yorkshire Police"), "offence_listed")
    assert c.status == "pass" and "actual bodily harm" in c.detail and c.link == v.LINK_DA_OFFENCES


@pytest.mark.parametrize("phrase", [
    "controlling or coercive behaviour in an intimate or family relationship (section 76 Serious Crime Act 2015)",
    "common assault (section 39 Criminal Justice Act 1988)",
    "harassment (section 2 Protection from Harassment Act 1997)",
    "threats to kill (section 16 Offences Against the Person Act 1861)",
    "criminal damage (section 1 Criminal Damage Act 1971)",
    "stalking", "rape", "sexual assault", "breach of a non-molestation order", "non-fatal strangulation", "GBH",
])
def test_offence_listed_categories(offline, phrase):
    text = f"WEST YORKSHIRE POLICE\nRECORD OF SIMPLE CAUTION\nName of person cautioned: Daniel Hughes\nOffence: {phrase}\nVictim: Sarah Okafor"
    assert by_id(run(text, "2"), "offence_listed").status == "pass"


def test_offence_not_on_list_warns(offline):
    c = by_id(run(CAUTION_NON_DA, "2", author_org="West Yorkshire Police"), "offence_listed")
    assert c.status == "warn" and "possession of a controlled drug" in c.detail and "check it is on the list" in c.detail
    text = "Defendant: Daniel Hughes\nCharge: being drunk and disorderly in a public place (section 91 Criminal Justice Act 1967) outside a bar in Leeds\nOutcome: bound over"
    assert by_id(run(text, "5"), "offence_listed").status == "warn"


def test_offence_none_named_is_unknown_and_only_for_paras_1_to_5(offline):
    text = "West Yorkshire Police – INCIDENT LOG\nSummary: Caller reports arguments. Officers attended. No offences disclosed.\nResult: Advice given."
    assert by_id(run(text, "2"), "offence_listed").status == "unknown"
    assert by_id(run(P1_POLICE_EMAIL, "7"), "offence_listed") is None


# --------------------------------------------------------------------------- relevance, order, robustness
def test_only_relevant_checks_are_returned(offline):
    # MoJ support-organisation letters: no email, URL (gov.uk only), postcode or register: nothing to show
    for case in ("MOJ-P17-accepted-01", "MOJ-P14-accepted-01", "MOJ-P19-accepted-01"):
        d = GOLD[case]["documents"][0]
        checks = run(d["text"], d["claimed_para"], author_org={"MOJ-P19-accepted-01": "Bath and Northeast Somerset Council"}.get(case))
        assert checks == [], case
    # a rich police email yields several, in the stable order, with no duplicate ids
    checks = run(P1_POLICE_EMAIL + "\nwww.northgate-das.org.uk", "1", author_org="West Yorkshire Police")
    ids = [c.id for c in checks]
    assert ids == sorted(ids, key=v.CHECK_ORDER.index) and len(ids) == len(set(ids))
    assert all(c.status in ("pass", "warn", "fail", "unknown") for c in checks)


def test_timeout_yields_unknown_without_raising(monkeypatch):
    async def slow_json(url, *, timeout, headers=None):
        await asyncio.sleep(5)

    async def slow_text(url, *, timeout, max_bytes=v.MAX_PAGE_BYTES):
        await asyncio.sleep(5)

    monkeypatch.setattr(v, "_http_get_json", slow_json)
    monkeypatch.setattr(v, "_http_get_text", slow_text)
    t0 = time.perf_counter()
    checks = run(P1_POLICE_EMAIL + "\nhttps://www.northgate-das.org.uk/", "1", author_org="West Yorkshire Police", timeout=0.2)
    assert time.perf_counter() - t0 < 2
    assert by_id(checks, "postcode_area").status == "unknown" and "could not run" in by_id(checks, "postcode_area").detail
    assert by_id(checks, "website_reachable").status == "unknown"
    assert by_id(checks, "official_domain").status == "pass"  # offline checks still answer


def test_never_raises(monkeypatch):
    async def boom(url, *, timeout, headers=None):
        raise RuntimeError("network exploded")

    async def boom_text(url, *, timeout, max_bytes=v.MAX_PAGE_BYTES):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(v, "_http_get_json", boom)
    monkeypatch.setattr(v, "_http_get_text", boom_text)
    checks = run(P1_POLICE_EMAIL + "\nhttps://www.northgate-das.org.uk/", "1", author_org="West Yorkshire Police")
    assert by_id(checks, "postcode_area").status == "unknown" and by_id(checks, "website_reachable").status == "unknown"
    assert run(None, "1") == []
    assert run("", None) == []
    assert run(P1_POLICE_EMAIL, None, author_org="West Yorkshire Police")  # no rule: still the generic checks


def test_fifty_urls_and_garbage_with_broken_network(monkeypatch):
    async def boom(url, *, timeout, headers=None):
        raise ConnectionError("x")

    async def boom_text(url, *, timeout, max_bytes=v.MAX_PAGE_BYTES):
        raise ConnectionError("x")

    monkeypatch.setattr(v, "_http_get_json", boom)
    monkeypatch.setattr(v, "_http_get_text", boom_text)
    fifty = "\n".join(f"https://site{i}.example.invalid/page{i}" for i in range(50)) + "\nLS1 4AP\nWest Yorkshire Police"
    checks = run(fifty, "17", author_org="Org", timeout=1.0)
    assert len([c for c in checks if c.id == "website_reachable"]) == 3
    assert all(c.status == "unknown" and "could not run" in c.detail for c in checks if c.id in ("website_reachable", "postcode_area"))
    import random, string
    rnd = random.Random(1)
    garbage = "".join(rnd.choice(string.printable) for _ in range(20000))
    t0 = time.perf_counter()
    checks = run(garbage, "17", author_org="Org", timeout=1.0)
    assert time.perf_counter() - t0 < 2 and all(c.status in ("pass", "warn", "fail", "unknown") for c in checks)


def test_bad_timeout_values_still_return_offline_checks(offline):
    for bad in ("abc", None, float("nan"), -5, 0):
        checks = run(P11_GP, "11", author_org="Riverside Medical Centre", timeout=bad)
        assert by_id(checks, "registration") is not None, bad


def test_find_urls_skips_ip_literals_localhost_and_govuk():
    text = ("http://169.254.169.254/latest/meta-data http://127.0.0.1:8000/admin http://localhost/x https://[::1]/ "
            "http://10.0.0.5/ https://www.gov.uk/legal-aid www.northgate-das.org.uk https://example.org/a.")
    assert v._find_urls(text) == ["https://www.northgate-das.org.uk", "https://example.org/a"]


def test_no_pass_detail_claims_verification(offline):
    # a format check or a built-in list match is never described as "verified"/"confirmed"
    texts = [(P1_POLICE_EMAIL + "\nwww.northgate-das.org.uk", "1", "West Yorkshire Police"), (P11_GP, "11", "Riverside Medical Centre"),
             (P17_SUPPORT_ORG, "17", "Northgate Domestic Abuse Service"), (DAPN, "6A", "Greater Manchester Police"),
             ("Refuge\nLondon SW1A 2AA", "18", "Refuge"), (MARAC, "13", "Bath and Northeast Somerset Council")]
    seen = set()
    for text, para, org in texts:
        for c in run(text, para, author_org=org):
            seen.add(c.id)
            if c.status == "pass":
                assert not re.search(r"\bverified\b|\bconfirmed\b|\bauthenticated\b(?! from)", c.detail, re.I), (c.id, c.detail)
            if c.id == "registration":
                assert c.status != "pass"
    assert seen >= {"official_domain", "website_reachable", "postcode_area", "registration", "charity_register", "dapn_pilot", "offence_listed"}


def test_http_helpers_degrade_without_raising():
    # an unroutable address: both helpers return their failure value instead of raising
    assert asyncio.run(v._http_get_json("http://10.255.255.1/x", timeout=0.3)) is None
    fetched = asyncio.run(v._http_get_text("http://10.255.255.1/x", timeout=0.3))
    assert fetched.status is None and fetched.error


# --------------------------------------------------------------------------- live
def _online() -> bool:
    try:
        socket.create_connection(("api.postcodes.io", 443), timeout=2).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _online(), reason="no network")
def test_live_postcodes_io_metropolitan_police():
    data = asyncio.run(v._http_get_json(v.POSTCODES_API.format(postcode="SW1A%202AA"), timeout=4.0))
    assert data and data["status"] == 200
    pfa = data["result"]["pfa"]
    assert "Metropolitan Police" in pfa  # postcodes.io returns "Metropolitan Police"
    assert v._forces_match("Metropolitan Police Service", pfa)
    assert data["result"]["admin_district"] == "Westminster"
