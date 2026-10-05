"""Every format a client or solicitor can upload reaches the engine as text or as an image the model can read."""
import io
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from engine.ingest import UnsupportedFile, ingest

FIX = Path(__file__).parent / "fixtures"
PNG = FIX / "moj_p11_rejected.png"


def test_heic_iphone_photo_is_converted_to_jpeg():
    pillow_heif = pytest.importorskip("pillow_heif")
    pillow_heif.register_heif_opener()
    img = Image.open(PNG).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "HEIF", quality=80)
    ing = ingest(buf.getvalue(), "IMG_0042.HEIC")
    assert ing.kind == "image" and ing.needs_transcription and ing.media_type == "image/jpeg"
    back = Image.open(io.BytesIO(ing.data))
    assert back.format == "JPEG" and max(back.size) <= 2000
    assert "converted to JPEG for reading" in ing.notes


def test_oversized_photo_is_downscaled_and_rotated_by_exif():
    big = Image.new("RGB", (4000, 3000), "white")
    buf = io.BytesIO()
    big.save(buf, "JPEG")
    ing = ingest(buf.getvalue(), "photo.jpg")
    assert ing.media_type == "image/jpeg" and max(Image.open(io.BytesIO(ing.data)).size) == 2000


def test_native_png_is_passed_through_unchanged():
    data = PNG.read_bytes()
    ing = ingest(data, "letter.png")
    assert ing.media_type == "image/png" and ing.data == data and ing.needs_transcription


def test_tiff_is_converted_to_jpeg():
    img = Image.new("RGB", (800, 600), "white")
    buf = io.BytesIO()
    img.save(buf, "TIFF")
    ing = ingest(buf.getvalue(), "scan.tiff")
    assert ing.media_type == "image/jpeg" and Image.open(io.BytesIO(ing.data)).format == "JPEG"


def test_scanned_pdf_with_no_text_layer_goes_to_the_model():
    img = Image.new("RGB", (1200, 1600), "white")
    buf = io.BytesIO()
    img.save(buf, "PDF")
    ing = ingest(buf.getvalue(), "scan.pdf")
    assert ing.kind == "pdf" and ing.needs_transcription and ing.media_type == "application/pdf" and ing.data
    assert "scan" in ing.notes[0]


def test_text_layer_pdf_does_not_need_the_model():
    ing = ingest((FIX / "moj_p18_accepted.pdf").read_bytes(), "letter.pdf")
    assert not ing.needs_transcription and "refused admission to a refuge" in ing.text


@pytest.mark.skipif(not (shutil.which("textutil") or shutil.which("soffice")), reason="no .doc converter on this machine")
def test_word_97_doc_is_converted(tmp_path):
    src = tmp_path / "letter.txt"
    src.write_text("I can confirm that Jane Doe was refused admission to a refuge on 28th September 2026.")
    if shutil.which("textutil"):
        subprocess.run(["textutil", "-convert", "doc", str(src), "-output", str(tmp_path / "letter.doc")], check=True, capture_output=True)
    else:
        subprocess.run(["soffice", "--headless", "--convert-to", "doc", "--outdir", str(tmp_path), str(src)], check=True, capture_output=True)
    ing = ingest((tmp_path / "letter.doc").read_bytes(), "letter.doc")
    assert ing.kind == "doc" and "refused admission to a refuge" in ing.text


def test_email_keeps_headers_and_body():
    raw = (b"From: DC Fatima Morgan <morgan.5333@southwales.pnn.police.uk>\r\nTo: family@hartleymoss.co.uk\r\nSubject: RE: Sarah Mensah\r\n"
           b"Date: Fri, 4 Sep 2026 14:02:00 +0100\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nI can confirm that Craig Shah was arrested on 13 August 2026.\r\n")
    ing = ingest(raw, "police.eml")
    assert ing.kind == "email" and "From: DC Fatima Morgan" in ing.text and "was arrested on 13 August 2026" in ing.text


def test_docx_and_unsupported():
    ing = ingest((FIX / "case_a_p17_corrected.docx").read_bytes(), "letter.docx")
    assert ing.kind == "docx" and "reasonable professional judgement" in ing.text
    with pytest.raises(UnsupportedFile):
        ingest(b"PK", "archive.zip")
    with pytest.raises(UnsupportedFile):
        ingest(b"not an image", "broken.jpg")
