"""Verification checks on the author and organisation of a document.

verify_document() returns a list of VerificationCheck that help a caseworker confirm
quickly who wrote a letter and for which organisation. The checks never change the
verdict; they add evidence (and links where a person can look for themselves).

Guarantees
  * verify_document never raises. Anything unexpected becomes a status "unknown"
    check or an empty list.
  * Every network call goes through _http_get_json / _http_get_text (async httpx,
    timeout <= 4 s). A call that fails degrades to "unknown" with a detail saying
    the check could not run. Tests monkeypatch these two helpers.
  * Nothing that runs by default needs an API key. CHARITY_COMMISSION_API_KEY is
    optional and only switches the charity check from a built-in list to the live
    Charity Commission register.
  * Details are honest: "has the right format; verify on the register" is not
    "verified". Only checks relevant to the document are returned, so a plain
    letter with no email, URL or postcode does not produce a row of unknowns.

Checks (stable ids)
  official_domain    email domain of the author (pnn.police.uk, nhs.net, gov.uk ...)
  website_reachable  each non-gov.uk URL in the text is fetched and the page is
                     checked for the organisation's name
  postcode_area      UK postcodes looked up on postcodes.io and compared with the
                     police force or council named in the letter
  registration       GMC / NMC / HCPC / GDC / Social Work England numbers:
                     format check plus a link to the register
  charity_register   support organisations (paras 12 to 18) against a small list
                     of national charities, or the Charity Commission API
  dapn_pilot         paragraph 6A: issuing force against the DAPN pilot areas
  offence_listed     paragraphs 1 to 5: the offence against the gov.uk list
"""
from __future__ import annotations

import asyncio
import html as _html
import ipaddress
import math
import os
import re
from typing import Awaitable, Callable, NamedTuple
from urllib.parse import quote, urlsplit

import httpx
from rapidfuzz import fuzz

from engine.models import Classification, Parties, VerificationCheck
from engine.rules import Rule

MAX_PAGE_BYTES = 200_000
MAX_CALL_TIMEOUT = 4.0
USER_AGENT = "gateway-check/0.1 (+evidence verification)"

# --------------------------------------------------------------------------- #
# Links a person can open
# --------------------------------------------------------------------------- #
LINK_POLICE_AREA = "https://www.police.uk/pu/your-area/"
LINK_FIND_COUNCIL = "https://www.gov.uk/find-local-council"
LINK_GMC = "https://www.gmc-uk.org/registrants/{number}"  # gmc-uk.org/doctors/{n} redirects here
LINK_NMC = "https://www.nmc.org.uk/registration/search-the-register/"
LINK_HCPC = "https://www.hcpc-uk.org/check-the-register/"
LINK_GDC = "https://olr.gdc-uk.org/searchregister"
LINK_SWE = "https://www.socialworkengland.org.uk/registration/register-guide/"
LINK_CHARITY_SEARCH = "https://register-of-charities.charitycommission.gov.uk/en/charity-search?q={q}"
LINK_OSCR = "https://www.oscr.org.uk/about-charities/search-the-register/"
LINK_DAPN = "https://www.gov.uk/guidance/domestic-abuse-protection-notices-dapns-and-domestic-abuse-protection-orders-dapos"
# gov.uk/government/publications/domestic-violence-and-child-abuse-offences redirects here
LINK_DA_OFFENCES = "https://www.gov.uk/government/publications/domestic-abuse-and-child-abuse-offences-legal-aid-evidence"
CHARITY_API = "https://api.charitycommission.gov.uk/register/api/searchCharityName/{name}"
POSTCODES_API = "https://api.postcodes.io/postcodes/{postcode}"

# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #
OFFICIAL_DOMAIN_SUFFIXES = (
    "pnn.police.uk", "police.uk", "nhs.net", "nhs.uk", "nhs.scot", "hscni.net",
    "gov.uk", "cjsm.net", "cafcass.gov.uk",
)
OFFICIAL_DOMAIN_WORDS = {
    "pnn.police.uk": "a police (PNN) domain that only police staff can use",
    "police.uk": "a police domain",
    "nhs.net": "the NHSmail domain used by NHS staff",
    "nhs.uk": "an NHS domain",
    "nhs.scot": "an NHS Scotland domain",
    "hscni.net": "a Health and Social Care Northern Ireland domain",
    "gov.uk": "a government domain",
    "cjsm.net": "the Criminal Justice Secure Mail domain",
    "cafcass.gov.uk": "the Cafcass domain",
}
FREE_WEBMAIL = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.co.uk", "hotmail.fr", "outlook.com", "outlook.co.uk",
    "live.com", "live.co.uk", "msn.com", "yahoo.com", "yahoo.co.uk", "ymail.com", "rocketmail.com", "icloud.com",
    "me.com", "mac.com", "aol.com", "aol.co.uk", "protonmail.com", "proton.me", "pm.me", "gmx.com", "gmx.co.uk",
    "mail.com", "zoho.com", "yandex.com", "btinternet.com", "sky.com", "talktalk.net", "virginmedia.com",
    "blueyonder.co.uk", "ntlworld.com", "tiscali.co.uk", "mail.ru", "qq.com",
}

# Territorial police forces (postcodes.io "pfa" uses the area name without "Police"), plus the national ones.
POLICE_FORCES = [
    "Avon and Somerset", "Bedfordshire", "Cambridgeshire", "Cheshire", "City of London", "Cleveland", "Cumbria",
    "Derbyshire", "Devon and Cornwall", "Dorset", "Durham", "Dyfed-Powys", "Essex", "Gloucestershire",
    "Greater Manchester", "Gwent", "Hampshire and Isle of Wight", "Hampshire", "Hertfordshire", "Humberside", "Kent",
    "Lancashire", "Leicestershire", "Lincolnshire", "Merseyside", "Metropolitan", "Norfolk", "North Wales",
    "North Yorkshire", "Northamptonshire", "Northumbria", "Nottinghamshire", "South Wales", "South Yorkshire",
    "Staffordshire", "Suffolk", "Surrey", "Sussex", "Thames Valley", "Warwickshire", "West Mercia", "West Midlands",
    "West Yorkshire", "Wiltshire", "British Transport",
]
# postcodes.io "pfa" for the national areas: "Scotland" (Police Scotland); Northern Ireland postcodes have no pfa.
NATIONAL_FORCE_DISPLAY = {"scotland": "Police Scotland", "northern ireland": "Police Service of Northern Ireland"}
DAPN_PILOT_FORCES = {"greater manchester", "cleveland", "north wales", "british transport"}
DAPN_MET_BOROUGHS = ("Bromley", "Croydon", "Sutton")
DAPN_PILOT_WORDS = "Greater Manchester; the London boroughs of Bromley, Croydon and Sutton; Cleveland; North Wales; and the British Transport Police"

# Offences on the gov.uk list of domestic abuse offences (categories used by the synthetic
# generator plus the common ones). Patterns are matched case-insensitively.
DA_OFFENCES: dict[str, tuple[str, ...]] = {
    "actual bodily harm (ABH)": (r"actual bodily harm", r"\bABH\b", r"section 47 of the offences against the person"),
    "grievous bodily harm (GBH) or wounding": (r"grievous bodily harm", r"\bGBH\b", r"\bwounding\b"),
    "controlling or coercive behaviour": (r"controlling (?:or|and) coercive", r"coercive (?:or|and) controlling", r"coercive control",
                                          r"section 76 (?:of the )?serious crime act"),
    "common assault or battery": (r"common assault", r"assault by beating", r"\bbattery\b", r"section 39 (?:of the )?criminal justice act"),
    "assault": (r"\bassault(?:ed|ing|s)?\b",),
    "harassment": (r"\bharass(?:ment|ed|ing)\b", r"protection from harassment act"),
    "stalking": (r"\bstalk(?:ing|ed)\b",),
    "threats to kill": (r"threats? to kill", r"threaten(?:ed|ing) to kill"),
    "criminal damage": (r"criminal damage",),
    "rape": (r"\brape[ds]?\b",),
    "sexual assault": (r"sexual(?:ly)? (?:assault|touch)", r"assault by penetration"),
    "breach of a non-molestation order": (r"breach(?:ing|ed|es)? (?:of )?(?:a |the |an |his |her )?non[- ]?molestation order",),
    "breach of a restraining order": (r"breach(?:ing|ed|es)? (?:of )?(?:a |the |an |his |her )?restraining order",),
    "non-fatal strangulation or suffocation": (r"\bstrangulation\b", r"\bstrangl(?:ed|ing)\b", r"\bsuffocat(?:ion|ed|ing)\b"),
    "putting people in fear of violence": (r"fear of violence",),
    "malicious communications": (r"malicious communication",),
    "false imprisonment": (r"false imprisonment",),
    "kidnapping": (r"\bkidnap",),
    "attempted murder": (r"attempted murder",),
    "murder or manslaughter": (r"\bmurder\b", r"\bmanslaughter\b"),
    "arson": (r"\barson\b",),
    "affray": (r"\baffray\b",),
    "witness intimidation": (r"intimidat(?:ing|ion of) (?:a )?witness", r"witness intimidation"),
    "blackmail": (r"\bblackmail\b",),
    "disclosing private sexual photographs or films": (r"private sexual (?:photograph|image|film)", r"revenge porn", r"intimate image"),
    "threatening or abusive behaviour (Public Order Act)": (r"threatening,? abusive or insulting", r"section 4A? (?:of the )?public order act"),
}
_DA_OFFENCE_RES = {name: [re.compile(p, re.I) for p in pats] for name, pats in DA_OFFENCES.items()}
_OFFENCE_ANCHOR_RE = re.compile(
    r"(?:arrested (?:on suspicion of|for)|on suspicion of|charged with|charges?\s*:|offences?\s*:|convicted of|conviction for|"
    r"cautioned for|caution (?:was )?(?:administered|given|issued) (?:for|in respect of)|pleaded guilty to|found guilty of|"
    r"bound over (?:in connection with|following)|an offence of|the offence of)\s*(.+?)(?=[.;\n]|$)",
    re.I,
)

# Built-in list of national domestic abuse charities. Each number was read from the organisation's
# own website footer (re-checked 2026-10-05); it is NOT a live register lookup and the details say so.
# Local groups that share a name (e.g. "Leeds Women's Aid") are separate charities and deliberately do
# NOT match; they fall through to the register search link. Aliases in "shared" are names that
# independent local charities also use on their own, so a bare match is reported as unknown, not pass.
# (SafeLives is not listed: its website blocks automated requests, so its number could not be confirmed.)
KNOWN_CHARITIES: list[dict] = [
    {"name": "Women's Aid Federation of England", "number": "1054154", "register": "ccew",
     "aliases": ("women's aid", "womens aid", "women's aid federation of england", "women's aid federation"),
     "shared": ("women's aid", "womens aid"),
     "note": "Local Women's Aid groups are separate charities with their own numbers, so check the letterhead."},
    {"name": "Refuge", "number": "277424", "register": "ccew", "aliases": ("refuge",),
     "note": "Many organisations run refuges; this number is the national charity Refuge."},
    {"name": "Rape Crisis England & Wales", "number": "1155140", "register": "ccew",
     "aliases": ("rape crisis england and wales", "rape crisis england & wales", "rape crisis"),
     "shared": ("rape crisis",),
     "note": "Local Rape Crisis centres are separate charities with their own numbers."},
    {"name": "Victim Support", "number": "298028", "register": "ccew", "aliases": ("victim support",)},
    {"name": "Respect", "number": "1141636", "register": "ccew", "aliases": ("respect", "respect uk")},
    {"name": "Welsh Women's Aid", "number": "1140962", "register": "ccew", "aliases": ("welsh women's aid", "welsh womens aid")},
    {"name": "Surviving Economic Abuse", "number": "1173256", "register": "ccew", "aliases": ("surviving economic abuse",)},
    {"name": "ManKind Initiative", "number": "1089547", "register": "ccew", "aliases": ("mankind initiative", "the mankind initiative", "mankind")},
    {"name": "Galop", "number": "1077384", "register": "ccew", "aliases": ("galop",)},
    {"name": "Scottish Women's Aid", "number": "SC001099", "register": "oscr", "aliases": ("scottish women's aid", "scottish womens aid")},
]
PUBLIC_BODY_WORDS = re.compile(
    r"\b(council|borough|county|nhs|hospital|surgery|medical|health|practice|clinic|court|police|constabulary|cafcass|"
    r"home office|solicitors?|llp|ltd|limited|university|school|magistrates|probation|cps|crown prosecution)\b", re.I)

REGISTERS = {
    "GMC": {"label": "GMC number", "body": r"\bGMC\b|General Medical Council", "format": r"^\d{7}$",
            "shape": "7 digits", "link": LINK_GMC},
    "NMC": {"label": "NMC PIN", "body": r"\bNMC\b|Nursing (?:and|&) Midwifery Council|\bPIN\b", "format": r"^\d{2}[A-Z]\d{4}[A-Z]$",
            "shape": "two digits, a letter, four digits and a letter, like 12A3456E", "link": LINK_NMC},
    "HCPC": {"label": "HCPC registration", "body": r"\bHCPC\b|Health (?:and|&) Care Professions Council", "format": r"^[A-Z]{2,3}\d{4,6}$",
             "shape": "two or three letters then digits, like PA12345", "link": LINK_HCPC},
    "GDC": {"label": "GDC number", "body": r"\bGDC\b|General Dental Council", "format": r"^\d{5,6}$", "shape": "5 or 6 digits", "link": LINK_GDC},
    "SWE": {"label": "Social Work England number", "body": r"Social Work England|\bSWE\b", "format": r"^SW\d{3,7}$",
            "shape": "SW followed by digits, like SW12345", "link": LINK_SWE},
}
_PROFESSION_RE = re.compile(
    r"\b(doctor|dr\.?|general practitioner|gp|consultant|psychiatrist|physician|surgeon|clinician|nurse|health visitor|midwife|"
    r"paramedic|psychologist|radiographer|social worker|dentist|dental (?:nurse|hygienist|therapist))\b", re.I)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'()\[\]]+", re.I)
POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}[0-9][A-Z0-9]?) ?([0-9][A-Z]{2})\b")
COUNCIL_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z&'’\-]+|and|of|the|&|upon|on|under)(?:[ \t]+(?:[A-Z][A-Za-z&'’\-]+|and|of|the|&|upon|on|under))*)"
    r"[ \t]+(?:(?:Metropolitan[ \t]+)?Borough|City|District|County|Unitary|Town)?[ \t]*Council\b")
CHARITY_NO_RE = re.compile(r"charit(?:y|able)[^\n\d]{0,40}?\b(SC0\d{5}|NIC?\d{5,6}|\d{6,7})\b", re.I)
PAGE_NOISE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------- #
# HTTP helpers: the only places that touch the network. Tests monkeypatch them.
# --------------------------------------------------------------------------- #
class Fetched(NamedTuple):
    status: int | None   # HTTP status, or None when the request itself failed
    text: str
    error: str | None = None


async def _http_get_json(url: str, *, timeout: float, headers: dict[str, str] | None = None) -> dict | list | None:
    """GET a JSON document. Returns the parsed body (whatever the status), or None if the call failed."""
    timeout = min(timeout, MAX_CALL_TIMEOUT)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT, **(headers or {})}) as client:
            r = await client.get(url)
            return r.json()
    except Exception:
        return None


async def _http_get_text(url: str, *, timeout: float, max_bytes: int = MAX_PAGE_BYTES) -> Fetched:
    """GET a web page, following redirects, reading at most max_bytes. Never raises."""
    timeout = min(timeout, MAX_CALL_TIMEOUT)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.5"}) as client:
            async with client.stream("GET", url) as r:
                chunks: list[bytes] = []
                size = 0
                async for chunk in r.aiter_bytes():
                    chunks.append(chunk)
                    size += len(chunk)
                    if size >= max_bytes:
                        break
                body = b"".join(chunks)[:max_bytes]
                encoding = r.charset_encoding or "utf-8"
                try:
                    text = body.decode(encoding, errors="replace")
                except LookupError:
                    text = body.decode("utf-8", errors="replace")
                return Fetched(r.status_code, text, None)
    except httpx.TimeoutException:
        return Fetched(None, "", f"no response within {timeout:g} seconds")
    except httpx.HTTPError as e:
        return Fetched(None, "", _describe_http_error(e))
    except Exception as e:  # pragma: no cover - defensive
        return Fetched(None, "", type(e).__name__)


def _describe_http_error(e: httpx.HTTPError) -> str:
    name = type(e).__name__
    msg = str(e)
    if "nodename nor servname" in msg or "Name or service not known" in msg or "getaddrinfo" in msg or "Temporary failure in name resolution" in msg:
        return "the domain name does not resolve"
    if name == "ConnectError":
        return "connection refused or failed"
    return name


# --------------------------------------------------------------------------- #
# Small text helpers
# --------------------------------------------------------------------------- #
def _norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("&", " and ")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_force(s: str) -> str:
    """'Avon & Somerset Constabulary', 'Police Service of Northern Ireland', 'Metropolitan Police Service' -> the bare area name."""
    s = _norm(s)
    s = re.sub(r"\b(police|constabulary|service|force|of|the)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _force_display(pfa: str) -> str:
    """postcodes.io gives 'West Yorkshire', 'Devon & Cornwall', 'Metropolitan Police' or 'Scotland'; show a force name."""
    pfa = str(pfa)
    national = NATIONAL_FORCE_DISPLAY.get(_norm_force(pfa))
    if national:
        return national
    return pfa if "police" in pfa.lower() else f"{pfa} Police"


_POLICE_AUTHOR_RE = re.compile(r"\bpolice\b|\bconstabulary\b|\bthe met\b|\bPSNI\b|\bCPS\b|crown prosecution|witness care", re.I)


def _author_is_force(author_org: str | None, force: "NamedForce") -> bool:
    """Only compare a postcode with a force's area when the letter is from the police themselves, not a solicitor or
    council that merely mentions a force. With no classified organisation, assume the first force named is the author."""
    if not author_org or not author_org.strip():
        return True
    return bool(_POLICE_AUTHOR_RE.search(author_org)) or _forces_match(author_org, force.display)


def _forces_match(named: str, pfa: str) -> bool:
    a, b = _norm_force(named), _norm_force(pfa)
    return bool(a and b) and (a == b or a.startswith(b) or b.startswith(a))


def _norm_place(s: str) -> str:
    s = _norm(s)
    s = re.sub(r"\b(city of|royal borough of|borough of|metropolitan borough|borough|district|county|unitary|town|council|the)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _places_match(named: str, district: str) -> bool:
    a, b = _norm_place(named), _norm_place(district)
    if not a or not b:
        return False
    return fuzz.ratio(a.replace(" ", ""), b.replace(" ", "")) >= 85 or fuzz.token_set_ratio(a, b) >= 90


class NamedForce(NamedTuple):
    display: str
    key: str
    pos: int


def _find_force(text: str) -> NamedForce | None:
    """The first police force named in the text ("West Yorkshire Police", "Avon & Somerset Constabulary", ...)."""
    found: list[NamedForce] = []
    for name in POLICE_FORCES:
        words = [re.escape(w) for w in name.split()]
        pattern = r"\s+".join(w.replace("and", r"(?:and|&)") if w == "and" else w for w in words)
        if name == "Metropolitan":
            rx = re.compile(r"\bMetropolitan\s+Police(?:\s+Service)?\b|\bthe Met\b", re.I)
        else:
            rx = re.compile(rf"\b{pattern}\s+(?:Police(?:\s+Service)?|Constabulary)\b", re.I)
        m = rx.search(text)
        if m:
            display = ("Metropolitan Police Service" if name == "Metropolitan"
                       else re.sub(r"\s+", " ", m.group(0)).title().replace(" And ", " and ").replace(" Of ", " of ").replace(" & ", " and "))
            found.append(NamedForce(display, _norm_force(name), m.start()))
    for display, key, rx in (("Police Scotland", "scotland", r"\bPolice Scotland\b|\bPolice Service of Scotland\b"),
                             ("Police Service of Northern Ireland", "northern ireland", r"\bPolice Service of Northern Ireland\b|\bPSNI\b")):
        m = re.search(rx, text, re.I)
        if m:
            found.append(NamedForce(display, key, m.start()))
    if not found:
        return None
    found.sort(key=lambda f: f.pos)
    # "Hampshire" also matches inside "Hampshire and Isle of Wight"; keep the longer name at the same position
    return max((f for f in found if f.pos == found[0].pos), key=lambda f: len(f.display))


NOT_A_LOCAL_COUNCIL = re.compile(r"\b(medical|dental|midwifery|professions|legal|research|arts|sports|british|privy|security|press|advertising|film)\b", re.I)


def _find_council(text: str) -> str | None:
    m = next((x for x in COUNCIL_RE.finditer(text) if not NOT_A_LOCAL_COUNCIL.search(x.group(0))), None)
    if not m:
        return None
    name = m.group(1).strip()
    # Drop leading connectors ("the Eastbrook Borough Council"); "the Council" alone names nothing
    name = re.sub(r"^(?:(?:the|of|and|&|on|upon|under)\s*)+", "", name, flags=re.I).strip()
    return name or None


def _find_emails(text: str) -> list[str]:
    seen: list[str] = []
    for m in EMAIL_RE.finditer(text):
        e = m.group(0).strip(".,;:")
        if e.lower() not in {s.lower() for s in seen}:
            seen.append(e)
    return seen


def _author_email(text: str) -> str | None:
    """The From: address when there is one; otherwise the first address that is not in a To:/Cc: line."""
    for line in text.splitlines():
        if re.match(r"\s*from\s*:", line, re.I):
            m = EMAIL_RE.search(line)
            if m:
                return m.group(0)
    skip = set()
    for line in text.splitlines():
        if re.match(r"\s*(to|cc|bcc)\s*:", line, re.I):
            skip.update(e.lower() for e in _find_emails(line))
    for e in _find_emails(text):
        if e.lower() not in skip:
            return e
    return None


def _official_suffix(domain: str) -> str | None:
    d = domain.lower()
    hits = [s for s in OFFICIAL_DOMAIN_SUFFIXES if d == s or d.endswith("." + s)]
    return max(hits, key=len) if hits else None


def _find_urls(text: str) -> list[str]:
    urls: list[str] = []
    for m in URL_RE.finditer(text):
        u = m.group(0).rstrip(".,;:!?")
        if not u.lower().startswith("http"):
            u = "https://" + u
        try:
            host = (urlsplit(u).hostname or "").lower()
        except ValueError:
            continue
        if not host or "." not in host or host == "localhost":
            continue
        try:
            ipaddress.ip_address(host.strip("[]"))
            continue  # a bare IP address is never an organisation's website, and we never fetch internal addresses
        except ValueError:
            pass
        if host == "gov.uk" or host.endswith(".gov.uk"):
            continue  # guidance links, not the author's website
        if u not in urls:
            urls.append(u)
    return urls


def _find_postcodes(text: str) -> list[str]:
    out: list[str] = []
    for m in POSTCODE_RE.finditer(text):
        pc = f"{m.group(1)} {m.group(2)}"
        if pc not in out:
            out.append(pc)
    return out


def _page_text(html: str) -> str:
    t = PAGE_NOISE_RE.sub(" ", html)
    t = TAG_RE.sub(" ", t)
    return re.sub(r"\s+", " ", _html.unescape(t))


def _check(id: str, label: str, status: str, detail: str, link: str | None = None) -> VerificationCheck:
    return VerificationCheck(id=id, label=label, status=status, detail=detail, link=link)


def _could_not_run(id: str, label: str, what: str, link: str | None = None) -> VerificationCheck:
    return _check(id, label, "unknown", f"This check could not run ({what}). Nothing has been verified or ruled out.", link)


# --------------------------------------------------------------------------- #
# 1. official_domain
# --------------------------------------------------------------------------- #
def check_official_domain(text: str, classification: Classification) -> VerificationCheck | None:
    label = "Email domain"
    email = _author_email(text)
    if not email:
        if classification.document_kind == "email":
            return _check("official_domain", label, "unknown",
                          "The document looks like an email but no email address is visible, so the sender's domain cannot be checked. Ask for the original email with its headers.")
        return None
    domain = email.split("@", 1)[1].lower()
    suffix = _official_suffix(domain)
    if suffix:
        return _check("official_domain", label, "pass",
                      f"The author's address {email} is on {domain}, {OFFICIAL_DOMAIN_WORDS.get(suffix, 'an official domain')}. "
                      "This shows the organisation type of the address as written in the document, not who the person is; "
                      "an address typed or pasted into a document cannot be authenticated from the text.")
    if domain in FREE_WEBMAIL:
        return _check("official_domain", label, "warn",
                      f"The author's address {email} is a personal {domain} account. A professional letter would normally come from the organisation's own domain; confirm the author by another route (switchboard, register or letterhead).")
    return _check("official_domain", label, "unknown",
                  f"The author's address {email} is on {domain}, which is not a government, NHS or police domain. Check it matches the organisation's own website before relying on it.",
                  f"https://{domain}/")


# --------------------------------------------------------------------------- #
# 2. website_reachable
# --------------------------------------------------------------------------- #
async def check_website(url: str, author_org: str | None, timeout: float) -> VerificationCheck:
    label = "Website"
    host = urlsplit(url).hostname or url
    fetched = await _http_get_text(url, timeout=timeout)
    if fetched.status is None:
        return _check("website_reachable", label, "fail",
                      f"{host} could not be reached ({fetched.error or 'request failed'}). The site may not exist, may be down or may block automated requests; open the link yourself to check.", url)
    if not 200 <= fetched.status < 300:
        return _check("website_reachable", label, "warn",
                      f"{host} responded with HTTP {fetched.status}, so the page could not be read. Open it yourself and check it names {author_org or 'the organisation'}.", url)
    if not author_org:
        return _check("website_reachable", label, "unknown",
                      f"{host} is online, but the letter does not name an organisation to compare it with.", url)
    page = _page_text(fetched.text)
    score = fuzz.partial_ratio(_norm(author_org), _norm(page)) if page.strip() else 0
    if score >= 80:
        return _check("website_reachable", label, "pass",
                      f"{host} is online and the page names {author_org}. This shows the website matches the letterhead, not that the author works there.", url)
    return _check("website_reachable", label, "warn",
                  f"{host} is online but the page does not mention {author_org}. Check the letterhead and the website belong to the same organisation.", url)


# --------------------------------------------------------------------------- #
# 3. postcode_area
# --------------------------------------------------------------------------- #
async def _lookup_postcode(postcode: str, timeout: float) -> tuple[str, dict | None]:
    data = await _http_get_json(POSTCODES_API.format(postcode=quote(postcode)), timeout=timeout)
    if not isinstance(data, dict):
        return "error", None
    if data.get("status") == 200 and isinstance(data.get("result"), dict):
        return "ok", data["result"]
    if data.get("status") == 404:
        return "not_found", None
    return "error", None


def _tidy_district(name: object) -> str:
    return re.sub(r", (?:City|County) of$", "", str(name or ""))


async def check_postcode_area(text: str, timeout: float, author_org: str | None = None) -> VerificationCheck | None:
    label = "Postcode area"
    postcodes = _find_postcodes(text)[:2]
    if not postcodes:
        return None
    outcomes = await asyncio.gather(*[_lookup_postcode(pc, timeout) for pc in postcodes])
    resolved = [(pc, r) for pc, (kind, r) in zip(postcodes, outcomes) if kind == "ok"]
    missing = [pc for pc, (kind, _) in zip(postcodes, outcomes) if kind == "not_found"]
    force, council = _find_force(text), _find_council(text)
    if force and not _author_is_force(author_org, force):
        force = None  # a solicitor or council letter that mentions a force: do not judge its address by that force's area
    link = LINK_POLICE_AREA if force else (LINK_FIND_COUNCIL if council else None)
    if not resolved:
        if missing and len(missing) == len(postcodes):
            return _check("postcode_area", label, "warn",
                          f"{' and '.join(missing)} {'is' if len(missing) == 1 else 'are'} not a recognised UK postcode (not on postcodes.io). A wrong postcode on a letterhead is worth a second look.", link)
        return _could_not_run("postcode_area", label, "postcodes.io did not answer", link)

    parts = []
    for pc, r in resolved:
        district = _tidy_district(r.get("admin_district") or r.get("region") or r.get("country") or "an unknown area")
        pfa = r.get("pfa")
        parts.append(f"{pc} is in {district}; police force area {_force_display(pfa)}" if pfa else f"{pc} is in {district}")
    for pc in missing:
        parts.append(f"{pc} was not found")
    summary = ". ".join(parts) + "."

    if force:
        match = next(((pc, r) for pc, r in resolved if r.get("pfa") and _forces_match(force.display, r["pfa"])), None)
        if match:
            return _check("postcode_area", label, "pass", f"{summary} This matches the {force.display} named in the letter.", link)
        pfa = next((r["pfa"] for _, r in resolved if r.get("pfa")), None)
        if pfa:
            return _check("postcode_area", label, "fail",
                          f"{summary} The letter is from {force.display} but the address is in the {_force_display(pfa)} area. Check the letterhead and sender.", link)
        return _check("postcode_area", label, "unknown", f"{summary} No police force area is recorded for this postcode, so it cannot be compared with {force.display}.", link)
    if council:
        if any(_places_match(council, r.get("admin_district") or "") or _places_match(council, r.get("admin_county") or "") for _, r in resolved):
            return _check("postcode_area", label, "pass", f"{summary} This matches {council} Council named in the letter.", link)
        return _check("postcode_area", label, "warn",
                      f"{summary} The letter is from {council} Council, which is a different area. It may be a shared service or an old letterhead; check.", link)
    for _, r in resolved:
        district = _tidy_district(r.get("admin_district"))
        if district and re.search(rf"\b{re.escape(district)}\b", text, re.I):
            return _check("postcode_area", label, "pass", f"{summary} The letter also names {district}.", link)
    return _check("postcode_area", label, "unknown", f"{summary} Nothing else in the letter names a force, council or town to compare it with; check it matches the organisation's address.", link)


# --------------------------------------------------------------------------- #
# 4. registration
# --------------------------------------------------------------------------- #
class RegNumber(NamedTuple):
    body: str
    number: str | None   # None when the body is named but no number follows
    ok: bool


def _find_registrations(text: str) -> list[RegNumber]:
    found: list[RegNumber] = []
    for body, spec in REGISTERS.items():
        for m in re.finditer(spec["body"], text, re.I):
            window = text[m.end(): m.end() + 60]
            token = None
            for t in re.finditer(r"\b([A-Z]{0,3}\d[A-Z0-9]*)\b", window):
                if len(t.group(1)) >= 5:  # skip "11 years", dates and the like
                    token = t.group(1)
                    break
            if token is None:
                if not any(f.body == body for f in found):
                    found.append(RegNumber(body, None, False))
                continue
            if any(f.body == body and f.number == token for f in found):
                continue
            found = [f for f in found if not (f.body == body and f.number is None)]
            found.append(RegNumber(body, token, bool(re.match(spec["format"], token))))
    return found


def check_registration(text: str, rule: Rule | None) -> list[VerificationCheck]:
    label = "Registration"
    paragraph = rule.paragraph if rule else None
    regs = _find_registrations(text)
    if not regs and paragraph not in ("11", "12"):
        return []
    out: list[VerificationCheck] = []
    for r in regs:
        spec = REGISTERS[r.body]
        if r.number is None:
            continue  # the body is named without a number; handled below for para 11
        link = spec["link"].format(number=r.number) if "{number}" in spec["link"] else spec["link"]
        if r.ok:
            out.append(_check("registration", label, "unknown",
                              f"{spec['label']} {r.number} has the right format; verify on the register.", link))
        else:
            out.append(_check("registration", label, "warn",
                              f"{spec['label']} {r.number} does not have the usual format ({spec['shape']}); check it on the register.", link))
    if out:
        return out
    if paragraph == "11":
        bodies = [REGISTERS[r.body]["label"].split()[0] for r in regs]
        if bodies:
            spec = REGISTERS[regs[0].body]
            return [_check("registration", label, "warn",
                           f"The letter mentions the {spec['label'].split()[0]} register but gives no registration number; the LAA may ask for it.", spec["link"].replace("{number}", ""))]
        if not _PROFESSION_RE.search(text):
            return [_check("registration", label, "warn",
                           "No registration number and no registered profession (doctor, nurse, midwife, paramedic, psychologist, radiographer, dentist or social worker) is given; the LAA may ask for it.", None)]
    return []


# --------------------------------------------------------------------------- #
# 5. charity_register
# --------------------------------------------------------------------------- #
def _builtin_charity(org: str) -> tuple[dict, bool] | None:
    """The built-in charity whose name matches, and whether the matched name is one local groups also use."""
    n = _norm(org)
    for c in KNOWN_CHARITIES:
        for alias in c["aliases"]:
            if fuzz.ratio(n, _norm(alias)) >= 90:
                return c, alias in c.get("shared", ())
    return None


def _quoted_charity_numbers(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(1).upper() for m in CHARITY_NO_RE.finditer(text)))


def _pick_api_match(data: list, org: str) -> dict | None:
    best, best_score = None, 0
    for row in data:
        if not isinstance(row, dict):
            continue
        name = row.get("charity_name") or row.get("name") or ""
        score = fuzz.token_set_ratio(_norm(org), _norm(str(name)))
        registered = str(row.get("reg_status", "R")).upper().startswith("R") and not str(row.get("reg_status", "")).upper().startswith("RM")
        if score >= 90 and (score > best_score or (score == best_score and registered)):
            best, best_score = row, score
    return best


async def check_charity_register(text: str, classification: Classification, rule: Rule | None, timeout: float) -> VerificationCheck | None:
    label = "Charity register"
    org = (classification.author_org or "").strip()
    paragraph = rule.paragraph if rule else None
    if not org or paragraph not in {"12", "13", "14", "15", "16", "17", "18"}:
        return None
    if PUBLIC_BODY_WORDS.search(org):
        return None  # councils, NHS bodies, police, solicitors: not charities
    quoted = _quoted_charity_numbers(text)
    scottish = bool(re.search(r"\bscotland\b|\bscottish\b|\bSC0\d{5}\b", f"{org} {text}", re.I))
    search_link = LINK_CHARITY_SEARCH.format(q=quote(org))

    key = os.environ.get("CHARITY_COMMISSION_API_KEY")
    if key:
        data = await _http_get_json(CHARITY_API.format(name=quote(org)), timeout=timeout, headers={"Ocp-Apim-Subscription-Key": key})
        if isinstance(data, list):
            row = _pick_api_match(data, org)
            if row:
                number = str(row.get("reg_charity_number") or row.get("charity_number") or row.get("regno") or "").strip()
                name = row.get("charity_name") or row.get("name") or org
                if quoted and number and number not in quoted:
                    return _check("charity_register", label, "warn",
                                  f"The Charity Commission register lists {name} as charity {number}, but the letter quotes {quoted[0]}. Check which is right.", search_link)
                return _check("charity_register", label, "pass",
                              f"{name} is on the Charity Commission register (charity number {number or 'not returned'}). This confirms the organisation exists, not that the author works there.", search_link)
            return _check("charity_register", label, "unknown",
                          f"No charity called '{org}' was found on the Charity Commission register. Names on letters often differ from registered names, and not every support service is a charity; search the register.", search_link)
        # the API did not answer: fall back to the built-in list below

    hit = _builtin_charity(org)
    if hit:
        known, shared_name = hit
        link = LINK_OSCR if known["register"] == "oscr" else search_link
        reg = "OSCR" if known["register"] == "oscr" else "the Charity Commission"
        basis = (f"This is a name match against a built-in list of national charities; the number comes from the charity's own "
                 f"website, not from a live lookup of {reg}'s register, and it does not show the author works there.")
        if quoted and known["number"] not in quoted:
            return _check("charity_register", label, "warn",
                          f"'{org}' matches the name of {known['name']} (charity number {known['number']}), but the letter quotes charity number {quoted[0]}. "
                          f"{known.get('note', 'Check which is right.')} {basis}", link)
        if shared_name:
            return _check("charity_register", label, "unknown",
                          f"'{org}' is the name of the national charity {known['name']} (charity number {known['number']}), but independent local "
                          f"groups use the same name and have their own numbers, and the letter gives no number. Check the letterhead and search the register. {basis}", link)
        return _check("charity_register", label, "pass",
                      f"'{org}' matches the name of {known['name']}, charity number {known['number']}. {known.get('note', '')} {basis}".replace("  ", " "), link)
    detail = "Not found in the built-in list; search the register."
    if quoted:
        detail = f"Not found in the built-in list; the letter quotes charity number {quoted[0]}. Search the register to confirm it belongs to {org}."
    if scottish:
        detail += f" For a Scottish charity use OSCR: {LINK_OSCR}"
    return _check("charity_register", label, "unknown", detail, LINK_CHARITY_SEARCH.format(q=quote(quoted[0] if quoted else org)))


# --------------------------------------------------------------------------- #
# 6. dapn_pilot
# --------------------------------------------------------------------------- #
def check_dapn_pilot(text: str, rule: Rule | None) -> VerificationCheck | None:
    label = "DAPN pilot area"
    if not rule or rule.paragraph.upper() != "6A":
        return None
    force = _find_force(text)
    if not force:
        return _check("dapn_pilot", label, "unknown",
                      f"No issuing police force is named, so the notice cannot be matched to the DAPN pilot areas ({DAPN_PILOT_WORDS}).", LINK_DAPN)
    if force.key == "metropolitan":
        boroughs = [b for b in DAPN_MET_BOROUGHS if re.search(rf"\b{b}\b", text, re.I)]
        if boroughs:
            return _check("dapn_pilot", label, "pass",
                          f"Given by the Metropolitan Police Service and the notice names {boroughs[0]}, one of the three London pilot boroughs (Bromley, Croydon and Sutton).", LINK_DAPN)
        return _check("dapn_pilot", label, "warn",
                      "Given by the Metropolitan Police Service. Only Bromley, Croydon and Sutton are in the DAPN pilot and the notice does not name any of them; check the address is in one of those boroughs.", LINK_DAPN)
    if force.key in DAPN_PILOT_FORCES:
        extra = " British Transport Police can give DAPNs within the pilot areas." if force.key == "british transport" else ""
        return _check("dapn_pilot", label, "pass", f"Given by {force.display}, which is a DAPN pilot area.{extra}", LINK_DAPN)
    return _check("dapn_pilot", label, "fail",
                  f"Given by {force.display}, which is not in the DAPN pilot ({DAPN_PILOT_WORDS}). A DAPN from outside the pilot needs checking with the force before it is relied on.", LINK_DAPN)


# --------------------------------------------------------------------------- #
# 7. offence_listed
# --------------------------------------------------------------------------- #
def _match_offences(fragment: str) -> list[str]:
    names = [name for name, rxs in _DA_OFFENCE_RES.items() if any(rx.search(fragment) for rx in rxs)]
    if len(names) > 1 and "assault" in names:
        names.remove("assault")  # the specific assault category already covers it
    return names


def check_offence_listed(text: str, rule: Rule | None) -> VerificationCheck | None:
    label = "Offence on the list"
    if not rule or rule.paragraph not in {"1", "2", "3", "4", "5"}:
        return None
    anchored = [m.group(1).strip() for m in _OFFENCE_ANCHOR_RE.finditer(text) if m.group(1).strip()]
    if anchored:
        matched: list[str] = []
        for frag in anchored:
            matched += [n for n in _match_offences(frag) if n not in matched]
        if matched:
            return _check("offence_listed", label, "pass",
                          f"The offence named ({', '.join(matched[:3])}) matches an offence on the gov.uk list of domestic abuse offences.", LINK_DA_OFFENCES)
        frag = anchored[0]
        frag = frag if len(frag) <= 90 else frag[:87].rstrip() + "..."
        return _check("offence_listed", label, "warn",
                      f"The offence named ('{frag}') was not recognised as one on the gov.uk list of domestic abuse offences; check it is on the list.", LINK_DA_OFFENCES)
    matched = _match_offences(text)
    if matched:
        return _check("offence_listed", label, "pass",
                      f"The document mentions {', '.join(matched[:3])}, which is on the gov.uk list of domestic abuse offences, though it does not say in so many words what the arrest, charge or conviction was for.", LINK_DA_OFFENCES)
    return _check("offence_listed", label, "unknown",
                  "No offence is named, so it cannot be checked against the gov.uk list of domestic abuse offences.", LINK_DA_OFFENCES)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
CHECK_ORDER = ["official_domain", "website_reachable", "postcode_area", "registration", "charity_register", "dapn_pilot", "offence_listed"]
_LABELS = {"website_reachable": "Website", "postcode_area": "Postcode area", "charity_register": "Charity register"}


async def _run_network(tasks: list[tuple[str, str | None, Awaitable]], deadline: float) -> list[VerificationCheck]:
    """Run the network checks concurrently under one deadline; anything unfinished becomes 'unknown'."""
    if not tasks:
        return []
    futures = [asyncio.ensure_future(coro) for _, _, coro in tasks]
    done, pending = await asyncio.wait(futures, timeout=deadline)
    for f in pending:
        f.cancel()
    out: list[VerificationCheck] = []
    for (check_id, link, _), fut in zip(tasks, futures):
        if fut in pending:
            out.append(_could_not_run(check_id, _LABELS[check_id], f"no answer within {deadline:g} seconds", link))
            continue
        try:
            result = fut.result()
        except Exception as e:
            out.append(_could_not_run(check_id, _LABELS[check_id], type(e).__name__, link))
            continue
        if result is None:
            continue
        out.extend(result if isinstance(result, list) else [result])
    return out


async def verify_document(text: str, classification: Classification, parties: Parties, rule: Rule | None, *, timeout: float = 4.0) -> list[VerificationCheck]:
    """Run the verification checks relevant to this document. Never raises; network failures become 'unknown'."""
    try:
        try:
            t = float(timeout)
        except (TypeError, ValueError):
            t = 4.0
        if math.isnan(t) or t <= 0:
            t = 4.0 if math.isnan(t) else 0.1
        return await _verify(text if isinstance(text, str) else "", classification, rule, min(t, 60.0))
    except Exception:
        return []


async def _verify(text: str, classification: Classification, rule: Rule | None, timeout: float) -> list[VerificationCheck]:
    checks: list[VerificationCheck] = []
    if not text.strip():
        return checks

    def safe(fn: Callable[[], VerificationCheck | list[VerificationCheck] | None]) -> None:
        try:
            r = fn()
        except Exception:
            return
        if r is None:
            return
        checks.extend(r if isinstance(r, list) else [r])

    safe(lambda: check_official_domain(text, classification))
    safe(lambda: check_registration(text, rule))
    safe(lambda: check_dapn_pilot(text, rule))
    safe(lambda: check_offence_listed(text, rule))

    call_timeout = min(timeout, MAX_CALL_TIMEOUT)
    network: list[tuple[str, str | None, Awaitable]] = []
    for url in _find_urls(text)[:3]:
        network.append(("website_reachable", url, check_website(url, classification.author_org, call_timeout)))
    if _find_postcodes(text):
        network.append(("postcode_area", LINK_POLICE_AREA if _find_force(text) else None,
                        check_postcode_area(text, call_timeout, classification.author_org)))
    network.append(("charity_register", None, check_charity_register(text, classification, rule, call_timeout)))
    checks.extend(await _run_network(network, deadline=timeout + 0.5))

    order = {k: i for i, k in enumerate(CHECK_ORDER)}
    checks.sort(key=lambda c: order.get(c.id, len(order)))
    return checks
