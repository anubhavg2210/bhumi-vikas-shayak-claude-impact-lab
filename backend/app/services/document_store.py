"""Document Store for MP Bhumi Vikas Rules 2012."""
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Running page header printed at the top of every PDF page, e.g.
#   'Rule 56                M.P. Bhumi Vikas Rules, 2012                78'
#   'Rule 29-31             M.P. Bhumi Vikas Rules, 2012                49'
# The trailing number equals the 1-based PDF page number (verified for pages 2-108).
PAGE_HEADER_RE = re.compile(
    r"^[ \t]*Rules?[ \t]+[\w\-,& ]+?[ \t]+M\.P\.[ \t]+Bhumi[ \t]+Vikas[ \t]+Rules,[ \t]*2012[ \t]+(\d{1,3})[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
TABLE_COLUMN_ROW_RE = re.compile(r"^\(\d+\)\s+\(\d+\)")
PAGE_MARKER_RE = re.compile(r"^===== PDF page (\d+) =====$", re.MULTILINE)

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−"), "-")
_QUOTES = {ord("‘"): "'", ord("’"): "'", ord("“"): '"', ord("”"): '"', ord(" "): " "}


def normalize_text(text: str) -> str:
    """Normalize dashes, quotes, whitespace and case for robust verbatim comparison."""
    cleaned = text.translate(_DASHES).translate(_QUOTES)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().lower()


def strip_page_headers(text: str) -> str:
    return PAGE_HEADER_RE.sub("", text)


@dataclass
class RuleChunk:
    """A logical segment of a rule with its verified page number."""
    chunk_id: str
    rule_number: str
    rule_title: str
    part: str
    page_number: int
    text: str


@dataclass
class RuleRecord:
    """A complete regulatory rule record."""
    rule_number: str
    title: str
    part: str
    page_start: int
    page_end: int
    text: str
    chunks: List[RuleChunk] = field(default_factory=list)
    normalized_text: str = ""


class DocumentStore:
    """Manages ingestion, page resolution, and lookup of rules."""

    def __init__(self, data_file_path: Optional[Path] = None, page_text_path: Optional[Path] = None):
        self.data_file_path = Path(data_file_path) if data_file_path else settings.resolve_data_path("bhumi_vikas_rules.jsonl")
        if page_text_path is not None:
            self.page_text_path: Optional[Path] = Path(page_text_path)
        elif data_file_path is None:
            self.page_text_path = settings.resolve_data_path("bhumi_vikas_rules_fulltext_by_page.txt")
        else:
            self.page_text_path = None
        self.rules_by_number: Dict[str, RuleRecord] = {}
        self.chunks: List[RuleChunk] = []
        self.normalized_pages: Dict[int, str] = {}
        self._load_pages()
        self._load_documents()

    # ------------------------------------------------------------------ loading

    def _load_pages(self) -> None:
        """Load the per-page full text used to resolve and verify page numbers."""
        if not self.page_text_path or not self.page_text_path.is_file():
            logger.warning("Page text file not available; page numbers fall back to rule chunk pages.")
            return
        raw = self.page_text_path.read_text(encoding="utf-8")
        markers = list(PAGE_MARKER_RE.finditer(raw))
        for i, m in enumerate(markers):
            end = markers[i + 1].start() if i + 1 < len(markers) else len(raw)
            body = raw[m.end():end]
            self.normalized_pages[int(m.group(1))] = normalize_text(strip_page_headers(body))
        logger.info(f"Loaded page text for {len(self.normalized_pages)} PDF pages.")

    def _load_documents(self) -> None:
        """Load JSONL rules and create page-aware chunks."""
        if not self.data_file_path.exists():
            logger.warning(f"Data file not found at {self.data_file_path}. Document store is empty.")
            return

        logger.info(f"Loading rules from {self.data_file_path}")
        with open(self.data_file_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    rule_num = str(data["rule"]).strip()
                    page_start = int(data["page_start"])
                    text = str(data.get("text", "")).strip()
                    record = RuleRecord(
                        rule_number=rule_num,
                        title=str(data.get("title", "")).strip(),
                        part=str(data.get("part", "")).strip(),
                        page_start=page_start,
                        page_end=int(data.get("page_end", page_start)),
                        text=text,
                        normalized_text=normalize_text(strip_page_headers(text)),
                    )
                    record.chunks = self._generate_chunks(record)
                    self.rules_by_number[rule_num.upper()] = record
                    self.chunks.extend(record.chunks)
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Skipping malformed rule on line {line_no}: {e}")

        logger.info(f"Loaded {len(self.rules_by_number)} rules and {len(self.chunks)} chunks.")

    def _generate_chunks(self, rule: RuleRecord) -> List[RuleChunk]:
        """Split a rule text into page-mapped logical chunks."""
        # Split text into page segments at running headers
        segments = []
        current_page = rule.page_start
        last_idx = 0
        for match in PAGE_HEADER_RE.finditer(rule.text):
            seg_text = rule.text[last_idx:match.start()].strip()
            if seg_text:
                segments.append((current_page, seg_text))
            current_page = int(match.group(1))
            last_idx = match.end()
        remaining_text = rule.text[last_idx:].strip()
        if remaining_text:
            segments.append((current_page, remaining_text))
        if not segments:
            segments = [(rule.page_start, rule.text)]

        # Subdivide each page segment into manageable chunks (sub-rules or paragraphs)
        chunks: List[RuleChunk] = []
        chunk_counter = 0

        def emit(page_num: int, body: str) -> None:
            nonlocal chunk_counter
            chunk_counter += 1
            chunks.append(
                RuleChunk(
                    chunk_id=f"{rule.rule_number}_p{page_num}_{chunk_counter}",
                    rule_number=rule.rule_number,
                    rule_title=rule.title,
                    part=rule.part,
                    page_number=page_num,
                    text=body,
                )
            )

        for page_num, seg_text in segments:
            # Split by blank lines or numbered clauses like (1), (a), [1]
            sub_blocks = re.split(r"\n\s*\n|(?<=\n)(?=\s*\(\d+\)|\s*\(\w\)|\s*\[\d+\])", seg_text)
            buffer = ""
            for block in sub_blocks:
                block = (block or "").strip()
                if not block:
                    continue
                # A table column-header row like '(1)  (2)  (3)' belongs with the table heading above it.
                if buffer and TABLE_COLUMN_ROW_RE.match(block):
                    buffer = f"{buffer}\n{block}"
                    continue
                if len(buffer) + len(block) < 600:
                    buffer = f"{buffer}\n{block}" if buffer else block
                else:
                    if buffer:
                        emit(page_num, buffer)
                    buffer = block
            if buffer:
                emit(page_num, buffer)

        return chunks

    # ------------------------------------------------------------------ lookup

    def get_rule(self, rule_number: str) -> Optional[RuleRecord]:
        """Lookup rule by number (e.g. '56', '26-B')."""
        return self.rules_by_number.get(str(rule_number).strip().upper())

    def get_all_rules(self) -> List[RuleRecord]:
        return list(self.rules_by_number.values())

    def get_all_chunks(self) -> List[RuleChunk]:
        return self.chunks

    def find_rules_containing(self, excerpt: str) -> List[RuleRecord]:
        """Return every rule whose text contains the (normalized) excerpt verbatim."""
        needle = normalize_text(excerpt)
        if not needle:
            return []
        return [r for r in self.rules_by_number.values() if needle in r.normalized_text]

    def resolve_page_for_text(self, rule_number: str, text_snippet: str) -> Optional[int]:
        """Return the PDF page on which a verified snippet of a rule starts, or None if it cannot be confirmed."""
        rule = self.get_rule(rule_number)
        needle = normalize_text(text_snippet)
        if not rule or not needle:
            return None

        page_range = range(rule.page_start, rule.page_end + 1)
        if self.normalized_pages:
            for p in page_range:
                if needle in self.normalized_pages.get(p, ""):
                    return p
            # Snippet crosses a page break: the end of page p starts the snippet and
            # the start of page p+1 continues it. Report the page where it begins.
            head = needle[:15]
            for p in page_range:
                page = self.normalized_pages.get(p, "")
                next_page = self.normalized_pages.get(p + 1, "")
                idx = page.find(head)
                while idx != -1:
                    tail = page[idx:]
                    rest = needle[len(tail):].strip()
                    if needle.startswith(tail) and rest and next_page.startswith(rest):
                        return p
                    idx = page.find(head, idx + 1)

        # No page index (or snippet not located there): fall back to chunk pages.
        for chunk in rule.chunks:
            if needle in normalize_text(chunk.text):
                return chunk.page_number
        return None
