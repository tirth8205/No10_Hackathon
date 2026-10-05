"""Turn an uploaded file into text.

PDF   -> pypdf text; if the text is too thin it is treated as a scan and sent to
         the model as a document block for transcription.
DOCX  -> paragraphs and tables.  DOC -> converted with textutil (macOS) or LibreOffice.
Images-> JPEG/PNG/GIF/WEBP go to the model as an image block; HEIC/HEIF (iPhone
         photos), TIFF and BMP are converted to JPEG first; large photos are downscaled.
EML   -> headers and the text body.  TXT -> as is.

The original bytes stay in memory only. Nothing is written to disk except a
temporary file for .doc conversion, deleted immediately.
"""
from __future__ import annotations

import email
import email.policy
import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path, PurePath

from pypdf import PdfReader

NATIVE_IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
CONVERT_IMAGE_TYPES = {".heic", ".heif", ".tif", ".tiff", ".bmp"}
TEXT_TYPES = {".txt", ".md"}
MIN_CHARS_PER_PAGE = 50
MAX_IMAGE_SIDE = 2000
JPEG_QUALITY = 85


@dataclass
class Ingested:
    text: str
    kind: str  # pdf | docx | doc | image | text | email
    pages: int = 1
    needs_transcription: bool = False
    media_type: str | None = None
    data: bytes | None = None  # only kept when the model must read the file itself
    notes: list[str] = field(default_factory=list)


class UnsupportedFile(ValueError):
    pass


def ingest(data: bytes, filename: str) -> Ingested:
    ext = PurePath(filename).suffix.lower()
    if ext == ".pdf":
        return _pdf(data)
    if ext == ".docx":
        return _docx(data)
    if ext == ".doc":
        return _doc(data)
    if ext in NATIVE_IMAGE_TYPES:
        return _image(data, NATIVE_IMAGE_TYPES[ext])
    if ext in CONVERT_IMAGE_TYPES:
        return _image(data, None)
    if ext == ".eml":
        return _eml(data)
    if ext in TEXT_TYPES or not ext:
        return Ingested(text=_decode(data), kind="text")
    raise UnsupportedFile(f"unsupported file type {ext!r}; use PDF, Word, a photo (JPG, PNG, HEIC), email or text")


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _pdf(data: bytes) -> Ingested:
    reader = PdfReader(io.BytesIO(data))
    pages = [(p.extract_text() or "") for p in reader.pages]
    text = "\n\n".join(t.strip() for t in pages).strip()
    n = max(len(pages), 1)
    thin = len(text) < MIN_CHARS_PER_PAGE * n
    out = Ingested(text=text, kind="pdf", pages=n)
    if thin:
        out.needs_transcription = True
        out.media_type = "application/pdf"
        out.data = data
        out.notes.append("little or no text layer; treated as a scan")
    return out


def _docx(data: bytes) -> Ingested:
    from docx import Document  # imported lazily; python-docx is slow to import

    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return Ingested(text="\n".join(parts), kind="docx")


def _doc(data: bytes) -> Ingested:
    """Word 97-2003. textutil ships with macOS; LibreOffice's soffice works everywhere."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "upload.doc"
        src.write_bytes(data)
        if shutil.which("textutil"):
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(src)], capture_output=True, timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                return Ingested(text=_decode(r.stdout), kind="doc")
        if shutil.which("soffice"):
            subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text", "--outdir", tmp, str(src)], capture_output=True, timeout=90)
            out = Path(tmp) / "upload.txt"
            if out.exists():
                return Ingested(text=_decode(out.read_bytes()), kind="doc")
    raise UnsupportedFile("could not read this .doc file; save it as .docx or PDF and try again")


def _image(data: bytes, media_type: str | None) -> Ingested:
    """Normalise to something the model can read: HEIC/TIFF/BMP -> JPEG; oversized photos downscaled."""
    from PIL import Image, ImageOps

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:  # HEIC then fails below with a clear message
        pass
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as e:
        raise UnsupportedFile(f"could not read this image ({type(e).__name__}); try a JPG or PNG") from e
    img = ImageOps.exif_transpose(img)  # phone photos carry their rotation in EXIF
    needs_convert = media_type is None or max(img.size) > MAX_IMAGE_SIDE or img.mode not in ("RGB", "L", "RGBA", "P")
    if not needs_convert:
        return Ingested(text="", kind="image", needs_transcription=True, media_type=media_type, data=data)
    if max(img.size) > MAX_IMAGE_SIDE:
        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=JPEG_QUALITY)
    notes = [] if media_type else ["converted to JPEG for reading"]
    return Ingested(text="", kind="image", needs_transcription=True, media_type="image/jpeg", data=buf.getvalue(), notes=notes)


def _eml(data: bytes) -> Ingested:
    msg = email.message_from_bytes(data, policy=email.policy.default)
    body = msg.get_body(preferencelist=("plain", "html"))
    text = body.get_content() if body else ""
    if body is not None and body.get_content_type() == "text/html":
        import re

        text = re.sub(r"<[^>]+>", " ", text)
    head = "\n".join(f"{h}: {msg[h]}" for h in ("From", "To", "Date", "Subject") if msg[h])
    return Ingested(text=f"{head}\n\n{text}".strip(), kind="email")
