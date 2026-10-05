"""Synthetic evidence PDFs built from the 12 MoJ gold letters (data/moj_gold_cases.json).

Each gold case becomes two PDFs:

  data/moj_gold_pdfs/digital/<case-id>.pdf   a typed letter with a text layer
  data/moj_gold_pdfs/scanned/<case-id>.pdf   the same letter printed and scanned: images only,
                                             no text layer, so the engine sends it to the model to read

plus data/moj_gold_pdfs/manifest.json with the expected labels for every file.

What is added around MoJ's text, and what never is
  The body of every letter is MoJ's wording, copied character for character (typos and the
  unfilled "[name of applicant]" placeholder included). Around it the script adds what a real
  letter carries: a letterhead, a reference, a date, a salutation and a signature. Those parts
  are fictional, and are checked so they can never change an expected label:
    * no hedged or confirming wording, no "matters relied on", no description of support,
      no examination, no assessment, no refusal (FORBIDDEN_IN_DECORATION)
    * no name of the other party, and no applicant other than the case's own
    * a letter whose body names a real organisation (a council, Women's Aid) gets a plain header
      with no organisation in it, so no real body's letterhead is imitated
    * nothing real for the verification checks to look up: no charity numbers, postcodes or
      URLs; phone numbers come from Ofcom's ranges reserved for drama; email addresses use the
      reserved .example domain; the GMC number is 0000000
  Each PDF is marked as synthetic in its metadata (title, subject, keywords), which the engine
  does not read. The page itself carries no marker, so the engine sees exactly what it would see
  in a real upload.

The output is deterministic: rebuilding gives the same bytes. The committed PDFs (on master)
were built by this version.

Run from the repo root, where data/moj_gold_cases.json exists (the backend branch):
  uv run --with reportlab --with pypdfium2 python scripts/make_gold_pdfs.py
reportlab and pypdfium2 are only needed here, so they are not project dependencies.
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "data" / "moj_gold_cases.json"
OUT = ROOT / "data" / "moj_gold_pdfs"

SCAN_DPI = 150
SCAN_JPEG_QUALITY = 70
FIXED_PDF_DATE = datetime(2026, 10, 5, 9, 0, 0).timetuple()  # Pillow wants a struct_time; fixed so scans rebuild byte for byte
METADATA_SUBJECT = (
    "Synthetic test document built from MoJ example wording. The letterhead, names and contact details "
    "are fictional. Not genuine evidence."
)

# Never added by the script around MoJ's text (checked case-insensitively, on the spec and on the rendered page).
FORBIDDEN_IN_DECORATION = (
    "might", "may be", "possibly", "could be", "consistent", "matters", "relied", "judgement", "assessed",
    "refused", "admission", "providing", "provided", "supported", "support to", "examined", "victim",
    "perpetrator", "name of", "john doe", "[", "]", "http", "www.", "charity", "postcode",
)
APPLICANT_NAMES = ("Jane Doe", "Joe Bloggs", "Jane Smith")


# --------------------------------------------------------------------------- #
# The letters
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Letterhead:
    """A fictional organisation's letterhead. All contact details are reserved or fictional."""

    org: str
    address: str
    phone: str  # Ofcom drama ranges: 0113 496 0xxx, 0114 496 0xxx, 01632 960xxx
    email: str | None  # always @<name>.example
    accent: tuple[int, int, int]
    mark: str  # "circle" | "bars" | "leaf" | "square"


@dataclass(frozen=True)
class Letter:
    case_id: str
    letter_date: date
    ref: str
    letterhead: Letterhead | None  # None: the body names a real organisation, so no letterhead
    re_line: str | None
    salutation: str | None  # only when MoJ's body has none
    sign_off: tuple[str, ...] = ()  # only when MoJ's body has none; first line is the valediction
    font: str = "Helvetica"
    private: bool = False  # "Private and confidential" above the reference


BROOKFIELD = Letterhead(
    "Brookfield Women's Support Service", "Unit 4, Mill Court, Leeds", "0113 496 0742",
    "referrals@brookfield-support.example", (0, 102, 102), "circle")
MOORSIDE = Letterhead(
    "Moorside Domestic Abuse Service", "Moorside House, Station Road, Wakefield", "01632 960318",
    "help@moorside-das.example", (84, 44, 120), "bars")
NORTHFIELD = Letterhead(
    "Northfield Recovery Project", "3 Chapel Walk, Sheffield", "0114 496 0581",
    "hello@northfield-recovery.example", (0, 90, 48), "leaf")
RIVERSIDE = Letterhead(
    "Riverside Outreach and Advocacy", "The Old Mill, Water Lane, York", "01632 960447",
    "outreach@riverside-oa.example", (16, 52, 104), "square")
ELM_GROVE = Letterhead(
    "Elm Grove Medical Practice", "Elm Grove Health Centre, 2 Elm Grove, Leeds", "0113 496 0290",
    None, (40, 64, 88), "square")
SAFER_FUTURES = Letterhead(
    "Safer Futures IDVA Service", "Unit 9, Canal Wharf, Bradford", "01632 960214",
    "idva@saferfutures.example", (110, 30, 70), "circle")

GP_SIGN_OFF = ("Yours faithfully,", "Dr R. Hughes MBChB MRCGP", "General Practitioner", "GMC No. 0000000")

LETTERS = [
    Letter("MOJ-P17-accepted-01", date(2026, 9, 24), "Our ref: BWS/2026/0114", BROOKFIELD, "Re: Ms Jane Doe",
           "To whom it may concern",
           ("Yours faithfully,", "Sam Taylor", "Senior Domestic Abuse Support Worker", BROOKFIELD.org)),
    Letter("MOJ-P17-accepted-02", date(2026, 9, 25), "Our ref: MDAS/26/0471", MOORSIDE, "Re: Joe Bloggs",
           "To whom it may concern",
           ("Yours faithfully,", "Chris Allen", "Refuge and Outreach Worker", MOORSIDE.org), font="Times-Roman"),
    Letter("MOJ-P17-accepted-03", date(2026, 9, 22), "Our ref: NRP-2026-0233", NORTHFIELD, "Re: Jane Smith",
           "To whom it may concern",
           ("Yours faithfully,", "Robin Clarke", "Recovery Programme Coordinator", NORTHFIELD.org)),
    Letter("MOJ-P17-rejected-04", date(2026, 9, 29), "Our ref: ROA/2026/1182", RIVERSIDE, "Re: Joe Bloggs",
           "To whom it may concern",
           ("Yours faithfully,", "Lee Morgan", "Outreach Worker", RIVERSIDE.org), font="Times-Roman"),
    Letter("MOJ-P11-accepted-01", date(2026, 9, 29), "Our ref: EG/RH/0929", ELM_GROVE, "Re: Jane Doe",
           "To whom it may concern", GP_SIGN_OFF),
    Letter("MOJ-P11-rejected-02", date(2026, 9, 29), "Our ref: EG/RH/0929", ELM_GROVE, "Re: Jane Doe",
           "To whom it may concern", GP_SIGN_OFF),
    # The body is signed by a real council: plain header, no letterhead.
    Letter("MOJ-P19-accepted-01", date(2026, 10, 1), "Ref: FS/2026/7731", None, None, None, private=True),
    Letter("MOJ-P19-rejected-02", date(2026, 10, 1), "Ref: FS/2026/7731", None, None, None, private=True),
    # The body is signed for Women's Aid: plain header, no letterhead.
    Letter("MOJ-P18-accepted-01", date(2026, 9, 30), "Ref: RA/2026/0928", None, None, None,
           font="Times-Roman", private=True),
    Letter("MOJ-P18-rejected-02", date(2026, 9, 30), "Ref: RA/2026/0928", None, None, None,
           font="Times-Roman", private=True),
    Letter("MOJ-P14-accepted-01", date(2026, 10, 2), "Our ref: SF/IDVA/2026/0377", SAFER_FUTURES, None, None),
    Letter("MOJ-P14-rejected-02", date(2026, 10, 2), "Our ref: SF/IDVA/2026/0377", SAFER_FUTURES, None, None),
]


def long_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B')} {d.year}"


def decorations(letter: Letter) -> list[str]:
    """Every piece of text the script adds around MoJ's body."""
    parts = [letter.ref, long_date(letter.letter_date)]
    if letter.private:
        parts.append("Private and confidential")
    if letter.letterhead:
        lh = letter.letterhead
        parts += [lh.org, lh.address, f"Tel: {lh.phone}"] + ([f"Email: {lh.email}"] if lh.email else [])
    parts += [p for p in (letter.re_line, letter.salutation) if p]
    parts += list(letter.sign_off)
    return parts


def check_decorations(letter: Letter, applicant: str) -> None:
    """Refuse to build a letter whose added text could move an expected label."""
    own = applicant.replace("Ms ", "")
    for part in decorations(letter):
        low = part.lower()
        for word in FORBIDDEN_IN_DECORATION:
            if word in low:
                raise ValueError(f"{letter.case_id}: added text {part!r} contains {word!r}")
        for name in APPLICANT_NAMES:
            if name != own and name.lower() in low:
                raise ValueError(f"{letter.case_id}: added text {part!r} names another applicant ({name})")
    email = letter.letterhead.email if letter.letterhead else None
    if email and not email.endswith(".example"):
        raise ValueError(f"{letter.case_id}: email must use the reserved .example domain")


# --------------------------------------------------------------------------- #
# Digital PDF (reportlab)
# --------------------------------------------------------------------------- #
def _draw_mark(c, kind: str, x: float, y: float, size: float, rgb) -> None:
    """A simple geometric logo mark: shapes only, no text, so nothing is added to the text layer."""
    from reportlab.lib.colors import Color

    col = Color(*(v / 255 for v in rgb))
    c.setFillColor(col)
    c.setStrokeColor(col)
    if kind == "circle":
        c.circle(x + size / 2, y + size / 2, size / 2, stroke=0, fill=1)
        c.setFillColorRGB(1, 1, 1)
        c.circle(x + size * 0.62, y + size * 0.58, size * 0.2, stroke=0, fill=1)
    elif kind == "bars":
        w = size / 5
        for i, h in enumerate((0.45, 0.75, 1.0)):
            c.rect(x + i * w * 1.7, y, w, size * h, stroke=0, fill=1)
    elif kind == "leaf":
        p = c.beginPath()
        p.moveTo(x, y)
        p.curveTo(x, y + size, x + size, y + size, x + size, y + size)
        p.curveTo(x + size, y, x, y, x, y)
        c.drawPath(p, stroke=0, fill=1)
    else:
        c.rect(x, y, size, size, stroke=0, fill=1)
        c.setFillColorRGB(1, 1, 1)
        c.rect(x + size * 0.25, y + size * 0.25, size * 0.5, size * 0.5, stroke=0, fill=1)


def _signature_flowable(seed: int):
    """A pen squiggle drawn as a vector path (not text), seeded so it is stable."""
    from reportlab.platypus import Flowable

    class Signature(Flowable):
        def __init__(self) -> None:
            super().__init__()
            self.width, self.height = 48 * 2.8346, 13 * 2.8346

        def draw(self) -> None:
            rng = random.Random(seed)
            c = self.canv
            c.setStrokeColorRGB(0.08, 0.14, 0.42)
            c.setLineWidth(1.0)
            h = self.height
            # a tall opening loop, like a capital letter
            p = c.beginPath()
            x, y = 4.0, h * 0.35
            p.moveTo(x, y)
            p.curveTo(x + 2, y + h * 0.75, x + 14, y + h * 0.7, x + 9, y)
            p.curveTo(x + 6, y - h * 0.25, x + 1, y - h * 0.1, x + 13, y + h * 0.05)
            x += 13
            # running hand: loops that shrink and drift, as a pen tires
            for i in range(9):
                dx = rng.uniform(7, 12)
                rise = rng.uniform(0.25, 0.55) * h * (1 - i / 14)
                p.curveTo(x + dx * 0.2, y + rise, x + dx * 0.9, y + rise, x + dx * 0.55, y)
                p.curveTo(x + dx * 0.4, y - h * 0.08, x + dx * 0.8, y - h * 0.05, x + dx, y + rng.uniform(-1.5, 1.5))
                x += dx
            c.drawPath(p, stroke=1, fill=0)
            # a quick underline flourish
            u = c.beginPath()
            u.moveTo(10, h * 0.12)
            u.curveTo(x * 0.35, h * 0.02, x * 0.75, h * 0.2, x + 6, h * 0.1)
            c.setLineWidth(0.7)
            c.drawPath(u, stroke=1, fill=0)

    return Signature()


def build_digital(letter: Letter, body: str, seed: int) -> bytes:
    from reportlab.lib.colors import Color
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font, bold = letter.font, ("Helvetica-Bold" if letter.font == "Helvetica" else "Times-Bold")
    size = 10.5 if letter.font == "Helvetica" else 11.5
    grey = Color(0.33, 0.33, 0.33)
    text = ParagraphStyle("body", fontName=font, fontSize=size, leading=size * 1.38, spaceAfter=7)
    bullet = ParagraphStyle("bullet", parent=text, leftIndent=10, firstLineIndent=-10)
    small = ParagraphStyle("small", parent=text, fontSize=size - 1, textColor=grey, spaceAfter=0)
    small_right = ParagraphStyle("small_right", parent=small, alignment=TA_RIGHT)
    strong = ParagraphStyle("strong", parent=text, fontName=bold)
    tight = ParagraphStyle("tight", parent=text, spaceAfter=1)

    lh = letter.letterhead
    head_space = 32 * mm if lh else 4 * mm

    def first_page(c, doc) -> None:
        """Mark and name on the first row, contact details underneath, so nothing can overlap."""
        if not lh:
            return
        from reportlab.pdfbase.pdfmetrics import stringWidth

        c.saveState()
        rgb = lh.accent
        top = A4[1] - 16 * mm
        left = doc.leftMargin
        right = A4[0] - doc.rightMargin
        text_x = left + 15 * mm
        _draw_mark(c, lh.mark, left, top - 11 * mm, 11 * mm, rgb)
        c.setFillColor(Color(*(v / 255 for v in rgb)))
        c.setFont(bold, 15)
        c.drawString(text_x, top - 4.5 * mm, lh.org)
        c.setFillColor(grey)
        c.setFont(font, 8.5)
        contact = [f"Tel: {lh.phone}"] + ([f"Email: {lh.email}"] if lh.email else [])
        one_line = "  ·  ".join([lh.address, *contact])
        rows = [one_line] if stringWidth(one_line, font, 8.5) <= right - text_x else [lh.address, "  ·  ".join(contact)]
        for i, row in enumerate(rows):
            c.drawString(text_x, top - (9.5 + i * 3.8) * mm, row)
        c.setStrokeColor(Color(*(v / 255 for v in rgb)))
        c.setLineWidth(1.2)
        rule_y = top - (13.5 + (len(rows) - 1) * 3.8) * mm
        c.line(left, rule_y, right, rule_y)
        c.restoreState()

    story: list = [Spacer(1, head_space)]
    left_col = []
    if letter.private:
        left_col.append(Paragraph("Private and confidential", ParagraphStyle("pc", parent=small, fontName=bold, textColor=Color(0, 0, 0))))
    left_col.append(Paragraph(escape(letter.ref), small))
    meta = Table([[left_col, Paragraph(escape(long_date(letter.letter_date)), small_right)]], colWidths=["60%", "40%"])
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [meta, Spacer(1, 7 * mm)]
    if letter.re_line:
        story.append(Paragraph(escape(letter.re_line), strong))
    if letter.salutation:
        story.append(Paragraph(escape(letter.salutation), text))

    for para in body_paragraphs(body):
        style = bullet if para.startswith("- ") else text
        story.append(Paragraph(escape(para).replace("\n", "<br/>"), style))

    if letter.sign_off:
        valediction, *rest = letter.sign_off
        story += [Spacer(1, 2 * mm), Paragraph(escape(valediction), text), _signature_flowable(seed), Spacer(1, 1 * mm)]
        story += [Paragraph(escape(line), tight) for line in rest]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=25 * mm, rightMargin=25 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"Synthetic test letter – {letter.case_id}", author="Gateway Check test data",
        subject=METADATA_SUBJECT, keywords="synthetic, test data, not genuine evidence",
        creator="scripts/make_gold_pdfs.py", invariant=1,
    )
    doc.build(story, onFirstPage=first_page)
    return buf.getvalue()


def body_paragraphs(body: str) -> list[str]:
    return [p.strip("\n") for p in re.split(r"\n\s*\n", body) if p.strip()]


# --------------------------------------------------------------------------- #
# Scanned PDF: render the digital page, then make it look printed and scanned
# --------------------------------------------------------------------------- #
def build_scanned(digital: bytes, case_id: str, seed: int) -> tuple[bytes, int]:
    import pypdfium2 as pdfium
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    rng = random.Random(seed)
    pdf = pdfium.PdfDocument(digital)
    pages = []
    for i in range(len(pdf)):
        img = pdf[i].render(scale=SCAN_DPI / 72).to_pil().convert("L")
        # paper is never quite white, toner never quite black
        img = img.point(lambda v: 24 + v * (242 - 24) // 255)
        # a faint shadow along the left edge where the lid did not close
        shade = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(shade)
        for x in range(28):
            draw.line([(x, 0), (x, img.height)], fill=int(40 * (1 - x / 28)))
        img = ImageChops.subtract(img, shade)
        # sensor grain, seeded
        grain = Image.frombytes("L", img.size, rng.randbytes(img.width * img.height)).point(lambda v: v * 14 // 255)
        img = ImageChops.subtract(img, grain).filter(ImageFilter.GaussianBlur(0.55))
        # fed in slightly crooked
        img = img.rotate(rng.uniform(-0.9, 0.9), resample=Image.BICUBIC, expand=False, fillcolor=236)
        pages.append(img)
    pdf.close()

    buf = io.BytesIO()
    pages[0].save(
        buf, "PDF", save_all=True, append_images=pages[1:], resolution=float(SCAN_DPI), quality=SCAN_JPEG_QUALITY,
        title=f"Synthetic test scan – {case_id}", author="Gateway Check test data", subject=METADATA_SUBJECT,
        keywords="synthetic, test data, not genuine evidence, scanned", creator="scripts/make_gold_pdfs.py",
        producer="scripts/make_gold_pdfs.py", creationDate=FIXED_PDF_DATE, modDate=FIXED_PDF_DATE,
    )
    return buf.getvalue(), len(pages)


# --------------------------------------------------------------------------- #
# Checks on what was built
# --------------------------------------------------------------------------- #
def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extracted_text(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((p.extract_text() or "") for p in reader.pages), len(reader.pages)


def check_digital(letter: Letter, body: str, data: bytes) -> tuple[str, int]:
    """The text layer holds every body paragraph word for word, and nothing forbidden around it."""
    text, pages = extracted_text(data)
    flat = normalise(text)
    rest = flat
    for para in body_paragraphs(body):
        p = normalise(para)
        if p not in flat:
            raise AssertionError(f"{letter.case_id}: body paragraph not found in the text layer: {p[:80]!r}")
        rest = rest.replace(p, " ", 1)
    low = normalise(rest).lower()
    for word in FORBIDDEN_IN_DECORATION:
        if word in low:
            raise AssertionError(f"{letter.case_id}: rendered page has {word!r} outside MoJ's text: {normalise(rest)!r}")
    return text, pages


def check_scanned(case_id: str, data: bytes) -> None:
    text, _ = extracted_text(data)
    if text.strip():
        raise AssertionError(f"{case_id}: the scan has a text layer; it should be images only")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
def build(out: Path = OUT) -> dict:
    gold = {c["id"]: c for c in json.loads(GOLD.read_text())["cases"]}
    if set(gold) != {l.case_id for l in LETTERS}:
        raise SystemExit("data/moj_gold_cases.json and LETTERS list different cases")

    (out / "digital").mkdir(parents=True, exist_ok=True)
    (out / "scanned").mkdir(parents=True, exist_ok=True)
    entries = []
    for i, letter in enumerate(LETTERS):
        case = gold[letter.case_id]
        doc = case["documents"][0]
        body = doc["text"]
        check_decorations(letter, case["application"]["applicant"])

        digital = build_digital(letter, body, seed=100 + i)
        _, digital_pages = check_digital(letter, body, digital)
        scanned, scanned_pages = build_scanned(digital, letter.case_id, seed=200 + i)
        check_scanned(letter.case_id, scanned)

        (out / "digital" / f"{letter.case_id}.pdf").write_bytes(digital)
        (out / "scanned" / f"{letter.case_id}.pdf").write_bytes(scanned)
        lh = letter.letterhead
        entries.append({
            "case_id": letter.case_id,
            "claimed_para": doc["claimed_para"],
            "application": case["application"],
            "expected_overall": case["expected_overall"],
            "expected_outcome": doc["expected"]["outcome"],
            "expected_elements": {k: v["status"] for k, v in doc["expected"]["elements"].items()},
            "expected_reason": doc["expected"]["reason"],
            "letter": {
                "date": letter.letter_date.isoformat(),
                "reference": letter.ref,
                "letterhead": lh.org if lh else None,
                "added_text": decorations(letter),
                "all_added_text_is_fictional": True,
            },
            "files": {
                "digital": {"path": f"digital/{letter.case_id}.pdf", "pages": digital_pages, "text_layer": True,
                            "sha256": sha256(digital)},
                "scanned": {"path": f"scanned/{letter.case_id}.pdf", "pages": scanned_pages, "text_layer": False,
                            "dpi": SCAN_DPI, "sha256": sha256(scanned)},
            },
        })

    manifest = {
        "meta": {
            "description": (
                "Synthetic evidence PDFs built from data/moj_gold_cases.json by scripts/make_gold_pdfs.py. "
                "The body of each letter is MoJ's wording, unchanged; the letterhead, reference, date, salutation "
                "and signature are fictional and never add or remove anything an expected label depends on. "
                "digital/ has a text layer; scanned/ is images only and goes to the model for reading."
            ),
            "source": "data/moj_gold_cases.json",
            "n_cases": len(entries),
            "held_out": "Like the gold set, keep these as a held-out test set.",
        },
        "cases": entries,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def main() -> None:
    manifest = build()
    for e in manifest["cases"]:
        d, s = e["files"]["digital"], e["files"]["scanned"]
        print(f"{e['case_id']:<22} {e['expected_outcome']:<5} digital {d['pages']}p  scanned {s['pages']}p")
    print(f"wrote {len(manifest['cases']) * 2} PDFs and manifest.json to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
