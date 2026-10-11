"""Read text from user-uploaded documents: PDF (text layer or scanned), images, plain text.

Uploads are untrusted input. They are parsed in memory (never written to disk), size- and
page-limited, and identified by their content, not by filename or declared content type.
OCR is used only where there is no usable text layer, and every page records how it was read.
"""
import base64
import io
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

MIN_PAGE_TEXT_CHARS = 20          # below this a PDF page is treated as scanned
MAX_IMAGE_PIXELS = 40_000_000     # reject decompression bombs
OCR_MAX_SIDE_PX = 2000

ACCEPTED_TYPES = {
    "application/pdf": "PDF",
    "image/png": "PNG image",
    "image/jpeg": "JPEG image",
    "image/webp": "WebP image",
    "text/plain": "plain text",
}

# Words as they come out of PDFs set in the legacy Kruti Dev Hindi font (text extraction yields
# Latin glyphs, e.g. "fu;e" for नियम). Pages that look like this are re-read with OCR.
_KRUTI_DEV_TOKENS = {"fu;e", "ds", "dk", "dh", "esa", "gS", "vkSj", "fd", ";g", "Hkou", "Hkwfe", "fodkl", "vf/kfu;e", "izfr"}


class DocumentReadError(Exception):
    """The upload cannot be read. `status_code` is the HTTP status to return."""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ExtractedPage:
    number: int
    text: str
    method: str  # 'text_layer' | 'ocr' | 'plain_text'


@dataclass
class ExtractedDocument:
    filename: str
    media_type: str
    pages_total: int
    pages: List[ExtractedPage] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ocr_engine: Optional[str] = None
    ocr_is_generative: bool = False  # OCR done by an AI model
    truncated: bool = False

    @property
    def text(self) -> str:
        return "\n\n".join(f"[Page {p.number}]\n{p.text}" for p in self.pages if p.text.strip())

    @property
    def characters(self) -> int:
        return sum(len(p.text) for p in self.pages)

    @property
    def methods(self) -> List[str]:
        return sorted({p.method for p in self.pages if p.text.strip()})

    def page_text(self, number: int) -> Optional[str]:
        return next((p.text for p in self.pages if p.number == number), None)


# ---------------------------------------------------------------------------- OCR engines

class OcrEngine(ABC):
    name: str = "ocr"
    #: True when the engine is a generative model (may misread or normalise text).
    is_generative: bool = False

    @abstractmethod
    async def image_to_text(self, image) -> str:
        """Return the text printed in a PIL image."""


class CerebrasVisionOcr(OcrEngine):
    """OCR through an image-capable Cerebras model (Chat Completions with a base64 data URI)."""

    name = "cerebras-vision"
    is_generative = True

    PROMPT = (
        "Transcribe all text in this image exactly as printed, in its original language and script "
        "(English and/or Hindi). Keep every number, unit, and label exactly. Keep table rows on one line "
        "with cells separated by ' | '. Do not translate, summarise, correct, or add anything. "
        "Write [illegible] for text you cannot read. Output only the transcription."
    )

    def __init__(self, provider=None, model: Optional[str] = None):
        from backend.app.services.llm_provider import CerebrasLLMProvider
        self.provider = provider or CerebrasLLMProvider()
        self.model = model or settings.CEREBRAS_VISION_MODEL

    def is_available(self) -> bool:
        return self.provider.is_configured()

    async def image_to_text(self, image) -> str:
        from backend.app.services.llm_provider import LLMProviderError

        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=88)
        data_uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
        request = dict(
            model=self.model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": self.PROMPT},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]}],
            max_completion_tokens=4096,
            reasoning_effort="none",  # qwen-3.8-27b: 'none' disables reasoning; transcription needs none
            stream=False,
        )
        completion = await self.provider._create_with_retry(request)
        try:
            choice = completion.choices[0]
            text = choice.message.content or ""
        except (AttributeError, IndexError, TypeError):
            raise LLMProviderError("Unexpected Cerebras OCR response shape.", "bad_response") from None
        if getattr(choice, "finish_reason", None) == "length":
            text += "\n[transcription truncated]"
        return clean_extracted_text(text).strip()


def get_ocr_engine() -> Optional[OcrEngine]:
    choice = (settings.OCR_ENGINE or "auto").lower().strip()
    if choice == "none":
        return None
    if choice in ("auto", "cerebras"):
        engine = CerebrasVisionOcr()
        if engine.is_available():
            return engine
        if choice == "cerebras":
            logger.warning("OCR_ENGINE=cerebras but CEREBRAS_API_KEY is not set; OCR is disabled.")
        return None
    logger.warning(f"Unknown OCR_ENGINE '{choice}'; OCR is disabled.")
    return None


# ---------------------------------------------------------------------------- reader

def detect_media_type(data: bytes) -> Optional[str]:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if b"\x00" not in data[:4096]:
        try:
            data.decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return None
    return None


def looks_like_legacy_hindi_font(text: str) -> bool:
    tokens = re.findall(r"[^\s,.()]+", text)
    return sum(t in _KRUTI_DEV_TOKENS for t in tokens) >= 3


# Control characters (except tab/newline) and U+FFFD come from broken font-to-Unicode maps in
# PDF text layers, common with Devanagari fonts (e.g. "स्था" extracted as "\x00ा").
_BROKEN_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f�]")


def text_layer_is_damaged(text: str) -> bool:
    broken = len(_BROKEN_CHARS_RE.findall(text))
    return broken >= 3 or (broken > 0 and broken * 200 >= len(text))


def clean_extracted_text(text: str) -> str:
    return _BROKEN_CHARS_RE.sub("", text)


class DocumentReader:
    def __init__(self, ocr_engine: Optional[OcrEngine] = None, use_default_ocr: bool = True):
        self.ocr = ocr_engine if ocr_engine is not None else (get_ocr_engine() if use_default_ocr else None)

    async def read(self, filename: str, data: bytes) -> ExtractedDocument:
        if not data:
            raise DocumentReadError("The uploaded file is empty.")
        if len(data) > settings.UPLOAD_MAX_BYTES:
            raise DocumentReadError(
                f"The file is larger than the {settings.UPLOAD_MAX_BYTES // (1024 * 1024)} MB limit.", 413)
        media_type = detect_media_type(data)
        if media_type is None:
            raise DocumentReadError("Unsupported file type. Upload a PDF, PNG, JPEG, WebP image, or plain-text file.", 415)

        safe_name = re.sub(r"[^\w.\- ()ऀ-ॿ]", "_", (filename or "document"))[:120]
        if media_type == "application/pdf":
            doc = await self._read_pdf(safe_name, data)
        elif media_type == "text/plain":
            doc = self._read_text(safe_name, data)
        else:
            doc = await self._read_image(safe_name, media_type, data)

        self._cap_text(doc)
        if not any(p.text.strip() for p in doc.pages):
            hint = (" It appears to be scanned or an image, and OCR is not configured (set CEREBRAS_API_KEY)."
                    if self.ocr is None and media_type != "text/plain" else "")
            raise DocumentReadError("No readable text was found in the document." + hint)
        return doc

    # ---- formats

    def _read_text(self, filename: str, data: bytes) -> ExtractedDocument:
        text = clean_extracted_text(data.decode("utf-8-sig"))
        return ExtractedDocument(filename=filename, media_type="text/plain", pages_total=1,
                                 pages=[ExtractedPage(1, text.strip(), "plain_text")])

    async def _read_image(self, filename: str, media_type: str, data: bytes) -> ExtractedDocument:
        doc = ExtractedDocument(filename=filename, media_type=media_type, pages_total=1,
                                ocr_engine=self.ocr.name if self.ocr else None,
                                ocr_is_generative=bool(self.ocr and self.ocr.is_generative))
        if self.ocr is None:
            raise DocumentReadError("Images need OCR, which is not configured on this server (set CEREBRAS_API_KEY).")
        image = self._open_image(data)
        text = await self._ocr_page(doc, 1, image)
        doc.pages.append(ExtractedPage(1, text, "ocr"))
        return doc

    async def _read_pdf(self, filename: str, data: bytes) -> ExtractedDocument:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted and not reader.decrypt(""):
                raise DocumentReadError("The PDF is password-protected. Upload an unprotected copy.")
            pages_total = len(reader.pages)
        except DocumentReadError:
            raise
        except (PdfReadError, ValueError, KeyError, TypeError) as e:
            raise DocumentReadError(f"The PDF could not be read ({type(e).__name__}).") from None
        except Exception as e:  # pypdf can raise many things on malformed files
            if "decrypt" in str(e).lower() or "encrypt" in str(e).lower():
                raise DocumentReadError("The PDF is password-protected. Upload an unprotected copy.") from None
            raise DocumentReadError(f"The PDF could not be read ({type(e).__name__}).") from None

        doc = ExtractedDocument(filename=filename, media_type="application/pdf", pages_total=pages_total,
                                ocr_engine=self.ocr.name if self.ocr else None,
                                ocr_is_generative=bool(self.ocr and self.ocr.is_generative))
        limit = min(pages_total, settings.UPLOAD_MAX_PAGES)
        if pages_total > limit:
            doc.truncated = True
            doc.warnings.append(f"Only the first {limit} of {pages_total} pages were read.")

        needs_ocr: List[int] = []
        for i in range(limit):
            try:
                text = (reader.pages[i].extract_text() or "").strip()
            except Exception:
                text = ""
            legacy, damaged = looks_like_legacy_hindi_font(text), text_layer_is_damaged(text)
            if len(text) >= MIN_PAGE_TEXT_CHARS and not legacy and not damaged:
                doc.pages.append(ExtractedPage(i + 1, clean_extracted_text(text), "text_layer"))
            elif damaged and not legacy and self.ocr is None and len(text) >= MIN_PAGE_TEXT_CHARS:
                # A few broken characters: keep the cleaned text rather than nothing, and say so.
                # (Legacy-font text is unreadable gibberish, so it is not kept.)
                doc.pages.append(ExtractedPage(i + 1, clean_extracted_text(text), "text_layer"))
                doc.warnings.append(f"Page {i + 1} has a damaged text layer and OCR is not configured; "
                                    "some characters may be missing.")
            else:
                if legacy:
                    doc.warnings.append(f"Page {i + 1} uses a legacy Hindi font; it was re-read with OCR.")
                elif damaged:
                    doc.warnings.append(f"Page {i + 1} has a damaged text layer; it was re-read with OCR.")
                needs_ocr.append(i)

        if needs_ocr:
            await self._ocr_pdf_pages(doc, data, needs_ocr)
        doc.pages.sort(key=lambda p: p.number)
        return doc

    async def _ocr_pdf_pages(self, doc: ExtractedDocument, data: bytes, indexes: List[int]) -> None:
        if self.ocr is None:
            doc.warnings.append(
                f"{len(indexes)} page(s) have no text layer (scanned) and were skipped: OCR is not configured.")
            return
        import pypdfium2 as pdfium

        budget = settings.UPLOAD_MAX_OCR_PAGES
        selected, skipped = indexes[:budget], indexes[budget:]
        if skipped:
            doc.truncated = True
            doc.warnings.append(f"OCR is limited to {budget} pages per upload; "
                                f"{len(skipped)} scanned page(s) were not read.")
        pdf = pdfium.PdfDocument(data)
        try:
            for i in selected:
                page = pdf[i]
                width, height = page.get_size()
                scale = min(200 / 72, OCR_MAX_SIDE_PX / max(width, height, 1))
                image = page.render(scale=scale).to_pil().convert("RGB")
                text = await self._ocr_page(doc, i + 1, image)
                if text:
                    doc.pages.append(ExtractedPage(i + 1, text, "ocr"))
        finally:
            pdf.close()

    # ---- helpers

    @staticmethod
    def _open_image(data: bytes):
        from PIL import Image, ImageOps, UnidentifiedImageError

        try:
            with Image.open(io.BytesIO(data)) as probe:
                if probe.width * probe.height > MAX_IMAGE_PIXELS:
                    raise DocumentReadError("The image is too large to process.", 413)
            image = Image.open(io.BytesIO(data))
            image = ImageOps.exif_transpose(image).convert("RGB")
        except DocumentReadError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise DocumentReadError("The image could not be read.") from None
        image.thumbnail((OCR_MAX_SIDE_PX, OCR_MAX_SIDE_PX))
        return image

    async def _ocr_page(self, doc: ExtractedDocument, number: int, image) -> str:
        from backend.app.services.llm_provider import LLMProviderError

        try:
            return await self.ocr.image_to_text(image)
        except LLMProviderError as e:
            logger.error(f"OCR failed on page {number} ({e.reason}): {e}")
            doc.warnings.append(f"Page {number} could not be read by OCR ({e.reason}).")
            return ""

    @staticmethod
    def _cap_text(doc: ExtractedDocument) -> None:
        remaining = settings.UPLOAD_MAX_TEXT_CHARS
        kept: List[ExtractedPage] = []
        cut = False
        for page in doc.pages:
            if remaining <= 0:
                cut = True
                break
            if len(page.text) > remaining:
                page.text = page.text[:remaining]
                cut = True
            remaining -= len(page.text)
            kept.append(page)
        doc.pages = kept
        if cut:
            doc.truncated = True
            doc.warnings.append(f"The document text was cut to {settings.UPLOAD_MAX_TEXT_CHARS} characters for analysis.")
