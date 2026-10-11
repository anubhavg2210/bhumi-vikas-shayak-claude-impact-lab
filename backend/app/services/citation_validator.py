"""Citation validator ensuring all citations are strictly grounded in source rules."""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple
from backend.app.config import settings
from backend.app.models.schemas import Citation
from backend.app.services.document_store import DocumentStore, normalize_text

logger = logging.getLogger(__name__)

MIN_EXCERPT_CHARS = 12
MIN_EXCERPT_WORDS = 3
MAX_EXCERPT_CHARS = 1200

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
# Decimal numbers, or integers followed by a unit. Bare integers are too ambiguous
# (clause numbers, S.No. columns) to check reliably.
_NUMBER_RE = re.compile(
    r"(?<![\w.])(\d+\.\d+|\d+(?=\s*(?:m\b|meters?|metres?|mtrs?|sq|square|%|per\s*cent|hectares?|years?|days?|months?|मीटर|वर्ग|हेक्टेयर|वर्ष|दिन|प्रतिशत)))",
    re.IGNORECASE,
)


@dataclass
class ValidationReport:
    citations: List[Citation] = field(default_factory=list)
    rejected: int = 0
    stitched: int = 0  # citations accepted as ordered verbatim fragments (flattened tables)


MAX_FRAGMENTS = 3
MIN_FRAGMENT_WORDS = 3
MAX_SPAN_RATIO = 1.8


def match_fragments(quote: str, source: str) -> Optional[List[str]]:
    """Split `quote` into at most 3 verbatim fragments of `source`, in source order and close together.

    For flattened two-column tables, where the source interleaves cells (e.g. "Rs. 10.00 per square
    meter of the exclusively for residence. built up area.") and a model quotes one cell
    ("Rs. 10.00 per square meter of the built up area."). Every word of the quote must be covered by
    a fragment that occurs verbatim, so no figure can change. Returns None if it cannot be matched.
    """
    words = quote.split()
    norm_source = normalize_text(source)
    fragments: List[str] = []
    i, cursor, first_start, last_end = 0, 0, None, 0
    while i < len(words):
        best_j, best_pos = None, -1
        for j in range(len(words), i, -1):  # longest verbatim run starting at word i
            pos = norm_source.find(normalize_text(" ".join(words[i:j])), cursor)
            if pos != -1:
                best_j, best_pos = j, pos
                break
        if best_j is None:
            return None
        piece = " ".join(words[i:best_j])
        if best_j - i < MIN_FRAGMENT_WORDS:
            return None
        fragments.append(piece)
        if len(fragments) > MAX_FRAGMENTS:
            return None
        first_start = best_pos if first_start is None else first_start
        last_end = best_pos + len(normalize_text(piece))
        cursor = last_end
        i = best_j
    if len(fragments) < 2:
        return None  # a single fragment would have matched verbatim already
    if (last_end - first_start) > MAX_SPAN_RATIO * len(normalize_text(quote)):
        return None
    return fragments


def clip_passage(text: str, limit: int = 700) -> str:
    """Trim a passage at a line boundary so it stays a verbatim excerpt."""
    limit = min(limit, MAX_EXCERPT_CHARS)
    if len(text) <= limit:
        return text.strip()
    cut = text.rfind("\n", 0, limit)
    return text[: cut if cut > 100 else limit].strip()


def extract_numbers(text: str) -> List[float]:
    """Extract numeric quantities (decimals, or integers with a unit) from text."""
    values = []
    for m in _NUMBER_RE.finditer(text.translate(_DEVANAGARI_DIGITS)):
        try:
            values.append(float(m.group(1)))
        except ValueError:
            continue
    return values


def all_numbers(text: str) -> set:
    """Every number appearing in text, as floats (used as the 'supported' set)."""
    out = set()
    for tok in re.findall(r"\d+(?:\.\d+)?", text.translate(_DEVANAGARI_DIGITS)):
        try:
            out.add(float(tok))
        except ValueError:
            pass
    return out


class CitationValidator:
    """Validates citations against official regulatory texts to prevent hallucination."""

    def __init__(self, document_store: DocumentStore):
        self.doc_store = document_store

    def normalize_text(self, text: str) -> str:
        return normalize_text(text)

    def validate_excerpt_in_rule(self, rule_number: str, excerpt: str) -> Tuple[bool, Optional[int]]:
        """Verify the excerpt appears verbatim (modulo whitespace/case/dash style) in the rule.

        Returns (is_valid, page). Page is None when it cannot be confirmed; it is never guessed.
        """
        rule = self.doc_store.get_rule(rule_number) if rule_number else None
        if not rule or not self._excerpt_is_substantive(excerpt):
            return False, None
        if normalize_text(excerpt) not in rule.normalized_text:
            return False, None
        return True, self.doc_store.resolve_page_for_text(rule.rule_number, excerpt)

    @staticmethod
    def _excerpt_is_substantive(excerpt: str) -> bool:
        stripped = excerpt.strip()
        return (
            MIN_EXCERPT_CHARS <= len(stripped) <= MAX_EXCERPT_CHARS
            and len(stripped.split()) >= MIN_EXCERPT_WORDS
        )

    def validate_citations(
        self,
        citations: Iterable[Any],
        retrieved_rule_numbers: Optional[List[str]] = None,
    ) -> List[Citation]:
        return self.validate(citations, retrieved_rule_numbers).citations

    def validate(
        self,
        citations: Iterable[Any],
        retrieved_rule_numbers: Optional[List[str]] = None,
    ) -> ValidationReport:
        """Validate candidate citations from the model.

        A citation is kept only when its excerpt occurs verbatim in the source text.
        - rule_number given: the excerpt must occur in that rule (no silent re-attribution).
        - rule_number missing: the excerpt must occur in exactly one rule, preferring retrieved rules.
        The model-supplied page number and document title are ignored; both come from the source.
        """
        report = ValidationReport()
        seen = set()
        retrieved = {r.upper() for r in (retrieved_rule_numbers or [])}

        for raw in citations or []:
            if not isinstance(raw, dict):
                report.rejected += 1
                continue
            rule_num = str(raw.get("rule_number") or "").strip().upper()
            excerpt = re.sub(r"\s+", " ", str(raw.get("excerpt") or "")).strip()

            if not self._excerpt_is_substantive(excerpt):
                report.rejected += 1
                continue

            if rule_num:
                rule = self.doc_store.get_rule(rule_num)
            else:
                matches = self.doc_store.find_rules_containing(excerpt)
                preferred = [r for r in matches if r.rule_number.upper() in retrieved]
                pool = preferred or matches
                rule = pool[0] if len(pool) == 1 else None

            if not rule:
                logger.warning(f"Citation rejected: rule '{rule_num or '?'}' not found or ambiguous.")
                report.rejected += 1
                continue

            is_valid, page = self.validate_excerpt_in_rule(rule.rule_number, excerpt)
            if not is_valid:
                logger.warning(f"Citation rejected: excerpt not found verbatim in Rule {rule.rule_number}: '{excerpt[:60]}'")
                report.rejected += 1
                continue

            key = (rule.rule_number, normalize_text(excerpt))
            if key in seen:
                continue
            seen.add(key)

            report.citations.append(
                Citation(
                    document_title=settings.DOCUMENT_TITLE,
                    rule_number=rule.rule_number,
                    page_number=page,
                    excerpt=excerpt,
                )
            )
        return report

    def validate_against_passages(self, citations: Iterable[Any], passages: List[Any]) -> ValidationReport:
        """Build citations only from the passages that were retrieved and sent to the model.

        Each model citation points at a passage and quotes it:
            {"passage_id": <1-based index into `passages`>, "quote": "<verbatim text>"}
        An empty quote cites the passage itself. Rule number, page and title always come from the
        retrieval record; a quote that is not verbatim in that passage is rejected.
        The legacy form {"rule_number", "excerpt"} is accepted only if the excerpt is verbatim
        in a retrieved passage of that rule.
        """
        report = ValidationReport()
        seen = set()
        for raw in citations or []:
            if not isinstance(raw, dict):
                report.rejected += 1
                continue
            quote = re.sub(r"\s+", " ", str(raw.get("quote") or raw.get("excerpt") or "")).strip()
            pid = raw.get("passage_id")

            if pid is not None:
                if isinstance(pid, bool) or not isinstance(pid, (int, str)) or not str(pid).strip().isdigit() \
                        or not 1 <= int(pid) <= len(passages):
                    logger.warning(f"Citation rejected: passage_id {pid!r} is not one of the {len(passages)} passages sent.")
                    report.rejected += 1
                    continue
                candidates = [passages[int(pid) - 1]]
                if not quote:
                    quote = re.sub(r"\s+", " ", clip_passage(candidates[0].text)).strip()
            else:
                rule_num = str(raw.get("rule_number") or "").strip().upper()
                candidates = [p for p in passages if not rule_num or p.rule_number.upper() == rule_num]

            if not self._excerpt_is_substantive(quote):
                report.rejected += 1
                continue
            needle = normalize_text(quote)
            # A quote may come from the passage or from its lead-in context (both verbatim source text).
            passage = next(
                (p for p in candidates
                 if needle in normalize_text(p.text) or needle in normalize_text(f"{getattr(p, 'context', '')}\n{p.text}")),
                None,
            )
            excerpt = quote
            if passage is None:
                # Flattened tables: accept a quote made of a few close, ordered, verbatim fragments,
                # and show exactly those fragments (joined by "…") rather than the reassembled text.
                for p in candidates:
                    fragments = match_fragments(quote, f"{getattr(p, 'context', '')}\n{p.text}")
                    if fragments:
                        passage, excerpt = p, " … ".join(fragments)
                        report.stitched += 1
                        break
            if passage is None:
                logger.warning(f"Citation rejected: quote not found verbatim in the retrieved passage(s): '{quote[:60]}'")
                report.rejected += 1
                continue

            key = (passage.rule_number, normalize_text(excerpt))
            if key in seen:
                continue
            seen.add(key)
            page_probe = excerpt.split(" … ")[0]
            page = self.doc_store.resolve_page_for_text(passage.rule_number, page_probe) or passage.page_number
            report.citations.append(Citation(
                document_title=settings.DOCUMENT_TITLE,
                rule_number=passage.rule_number,
                page_number=page,
                excerpt=excerpt,
            ))
        return report

    def unsupported_numbers(self, answer: str, evidence_texts: Iterable[str]) -> List[float]:
        """Numbers stated in the answer that appear in none of the evidence texts."""
        supported = set()
        for t in evidence_texts:
            supported |= all_numbers(t)
        return [n for n in extract_numbers(answer) if n not in supported]
