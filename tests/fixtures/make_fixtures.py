"""Build the file fixtures used by tests/test_ingest.py and tests/test_ingest_live.py.

  moj_p18_accepted.pdf       text-layer PDF of the MoJ paragraph 18 accepted refuge letter
  moj_p11_rejected.png       "phone photo" of the MoJ paragraph 11 REJECTED (hedged GP) letter
  moj_p11_rejected_p1.png    the same letter as two pages (first half)
  moj_p11_rejected_p2.png                                   (second half)
  case_a_p17_corrected.docx  DOCX of the paragraph 17 corrected support-organisation letter

All the letters are fictional (MoJ sample wording with placeholder names). Everything
is deterministic: the PDF is written by hand, the PNG noise comes from a seeded RNG, so
re-running the script reproduces the committed bytes (font permitting).

Run:  .venv/bin/python -m tests.fixtures.make_fixtures
"""
from __future__ import annotations

import io
import json
import random
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
GOLD = ROOT / "data" / "moj_gold_cases.json"
CASE_A = ROOT / "demo" / "files" / "case-a-support-letter-corrected.txt"

PDF_NAME = "moj_p18_accepted.pdf"
PNG_NAME = "moj_p11_rejected.png"
PNG_PAGES = ("moj_p11_rejected_p1.png", "moj_p11_rejected_p2.png")
DOCX_NAME = "case_a_p17_corrected.docx"
ALL = (PDF_NAME, PNG_NAME, *PNG_PAGES, DOCX_NAME)

FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial.ttf",            # macOS
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",         # Debian/Ubuntu
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


# --------------------------------------------------------------------------- #
# letters
# --------------------------------------------------------------------------- #
def gold_letter(case_id: str) -> str:
    cases = json.loads(GOLD.read_text())["cases"]
    case = next(c for c in cases if c["id"] == case_id)
    return case["documents"][0]["text"]


def p18_accepted_text() -> str:
    return gold_letter("MOJ-P18-accepted-01")


def p11_rejected_text() -> str:
    return gold_letter("MOJ-P11-rejected-02")


def p17_corrected_text() -> str:
    return CASE_A.read_text()


def split_halves(text: str) -> tuple[str, str]:
    """Split a letter into two 'pages' on a paragraph boundary."""
    paras = [p for p in text.split("\n\n") if p.strip()]
    cut = (len(paras) + 1) // 2
    return "\n\n".join(paras[:cut]), "\n\n".join(paras[cut:])


# --------------------------------------------------------------------------- #
# PDF: a minimal valid file written by hand, Helvetica, one Tj per line
# --------------------------------------------------------------------------- #
def _pdf_escape(line: str) -> bytes:
    data = line.encode("cp1252", errors="replace")  # WinAnsiEncoding: keeps curly quotes and dashes
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _pdf_lines(text: str, width: int = 88) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(para, width=width, break_long_words=False, break_on_hyphens=False) or [""])
    return lines


def make_pdf(text: str, font_size: int = 11, leading: int = 14) -> bytes:
    page_w, page_h, margin = 612, 792, 72
    per_page = (page_h - 2 * margin) // leading
    lines = _pdf_lines(text)
    chunks = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]

    objects: list[bytes] = []  # object n is objects[n-1]

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    catalog = add(b"")  # placeholder, filled once we know the pages object number
    pages_obj = add(b"")
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    page_ids = []
    for chunk in chunks:
        ops = [b"BT", f"/F1 {font_size} Tf".encode(), f"{leading} TL".encode(), f"{margin} {page_h - margin} Td".encode()]
        for line in chunk:
            ops.append(b"(" + _pdf_escape(line) + b") Tj")
            ops.append(b"T*")
        ops.append(b"ET")
        stream = b"\n".join(ops)
        contents = add(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page = add(f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {page_w} {page_h}] "
                   f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {contents} 0 R >>".encode())
        page_ids.append(page)
    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode()
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objects[pages_obj - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{n} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


# --------------------------------------------------------------------------- #
# PNG: a letter rendered like a phone photo (slight rotation, light grey noise)
# --------------------------------------------------------------------------- #
def _font(size: int):
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)  # Pillow >= 10.1 ships a scalable fallback


def _wrap_to_width(text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        words, cur = para.split(), ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if font.getlength(trial) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def make_photo(text: str, width: int = 1400, font_size: int = 30, rotate_deg: float = 1.0, noise: int = 14, seed: int = 7) -> bytes:
    from PIL import Image, ImageChops, ImageDraw

    font = _font(font_size)
    margin, line_h = 110, int(font_size * 1.45)
    lines = _wrap_to_width(text, font, width - 2 * margin)
    height = 2 * margin + line_h * len(lines)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = margin
    for line in lines:
        draw.text((margin, y), line, fill="black", font=font)
        y += line_h
    # a phone photo is never quite straight
    img = img.rotate(rotate_deg, resample=Image.BICUBIC, expand=True, fillcolor="white")
    # light grey sensor noise, deterministic
    rng = random.Random(seed)
    raw = rng.randbytes(img.width * img.height)
    grain = Image.frombytes("L", img.size, raw).point(lambda v: v * noise // 255)
    img = ImageChops.subtract(img, Image.merge("RGB", (grain, grain, grain))).convert("L")  # greyscale keeps the file small
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# DOCX
# --------------------------------------------------------------------------- #
def make_docx(text: str) -> bytes:
    from docx import Document

    doc = Document()
    for para in text.split("\n"):
        if para.strip():
            doc.add_paragraph(para.strip())
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
def build(out_dir: Path = HERE) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    made: dict[str, Path] = {}

    def write(name: str, data: bytes) -> None:
        (out_dir / name).write_bytes(data)
        made[name] = out_dir / name

    write(PDF_NAME, make_pdf(p18_accepted_text()))
    p11 = p11_rejected_text()
    write(PNG_NAME, make_photo(p11))
    first, second = split_halves(p11)
    write(PNG_PAGES[0], make_photo(first, seed=11))
    write(PNG_PAGES[1], make_photo(second, seed=13, rotate_deg=-0.8))
    write(DOCX_NAME, make_docx(p17_corrected_text()))
    return made


def verify(paths: dict[str, Path]) -> None:
    """Sanity checks: the PDF has a text layer with the letter's words; the images open."""
    from pypdf import PdfReader
    from PIL import Image

    text = "\n".join((p.extract_text() or "") for p in PdfReader(str(paths[PDF_NAME])).pages)
    for words in ("Name of perpetrator: John Doe", "refused admission to a refuge", "28th September 2026", "Women’s Aid"):
        assert words in text, f"PDF text layer is missing {words!r}:\n{text}"
    for name in (PNG_NAME, *PNG_PAGES):
        with Image.open(paths[name]) as im:
            assert im.format == "PNG" and im.width >= 1400, name
    from docx import Document

    paras = [p.text for p in Document(str(paths[DOCX_NAME])).paragraphs if p.text.strip()]
    assert any("regulation 33" in p for p in paras)


def main() -> None:
    paths = build()
    verify(paths)
    for name, p in paths.items():
        print(f"{p.relative_to(ROOT)}  {p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
