"""Document coverage and known post-coverage amendments.

Everything here is sourced from files in this repository. The amendment registry
records only that a change exists and where the project says so; it deliberately
does not paraphrase the amended text, because that text is not in the collection.
"""
import re
from dataclasses import dataclass, asdict
from datetime import date
from typing import Dict, Iterable, List, Optional
from backend.app.config import settings


@dataclass(frozen=True)
class KnownAmendment:
    rule_number: str
    provision: str
    date: str
    source: str
    in_collection: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


# Source: data/DATA_DICTIONARY.md, "Things to know" section:
#   "Not included: the 28 Aug 2026 amendment to Rule 2(5)(c) and any other change
#    after 6 Mar 2025."
KNOWN_POST_COVERAGE_AMENDMENTS: List[KnownAmendment] = [
    KnownAmendment(
        rule_number="2",
        provision="Rule 2(5)(c)",
        date="2026-08-28",
        source="data/DATA_DICTIONARY.md",
    ),
]

FRESHNESS_LIMITATIONS: List[str] = [
    "The collection is the Government of Madhya Pradesh consolidation of the rules up to 6 March 2025.",
    "Amendments notified after 6 March 2025 are not included. The project records at least one "
    "(Rule 2(5)(c), 28 August 2026) whose text is not available in this repository.",
    "No authoritative source for other post-March-2025 amendments was found in the repository; "
    "current applicability must be checked against the M.P. Rajpatra (Official Gazette).",
    "The Hindi PDF uses a legacy (Kruti Dev) font encoding and cannot be text-indexed; Hindi "
    "questions are answered from the English consolidated text, and excerpts are quoted in English.",
]

_YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
_RECENCY_TERMS = (
    "latest", "recent amendment", "new amendment", "amended recently", "current rule",
    "currently", "as of today", "नवीनतम", "हाल ही", "नया संशोधन", "वर्तमान",
)


def coverage_date() -> date:
    return date.fromisoformat(settings.DOCUMENT_COVERAGE_DATE)


def question_mentions_post_coverage(question: str) -> bool:
    """True if the question refers to a year after the coverage date or asks about 'latest' rules."""
    cutoff_year = coverage_date().year
    for y in _YEAR_RE.findall(question):
        if int(y) > cutoff_year:
            return True
    lower = question.lower()
    return any(term in lower for term in _RECENCY_TERMS)


def amendments_for_rules(rule_numbers: Iterable[str]) -> List[KnownAmendment]:
    wanted = {str(r).strip().upper() for r in rule_numbers if r}
    return [a for a in KNOWN_POST_COVERAGE_AMENDMENTS if a.rule_number.upper() in wanted]


def freshness_note(lang: str, amendments: List[KnownAmendment], post_coverage_question: bool) -> Optional[str]:
    """Build a short note for the answer text, or None when nothing needs flagging."""
    if not amendments and not post_coverage_question:
        return None
    cov = settings.DOCUMENT_COVERAGE_DATE
    if lang == "hi":
        parts = [f"सूचना: यह उत्तर 06 मार्च 2025 ({cov}) तक संकलित नियमों पर आधारित है; इसके बाद के संशोधन शामिल नहीं हैं।"]
        for a in amendments:
            parts.append(
                f"{a.provision} में {a.date} को संशोधन दर्ज है, जिसका पाठ इस संग्रह में उपलब्ध नहीं है।"
            )
        parts.append("कृपया वर्तमान प्रावधान की पुष्टि म.प्र. राजपत्र से करें।")
    else:
        parts = [f"Note: this answer is based on the rules as consolidated up to {cov}; later amendments are not included."]
        for a in amendments:
            parts.append(
                f"{a.provision} is recorded as amended on {a.date}; the amended text is not in this collection."
            )
        parts.append("Verify the current provision against the M.P. Rajpatra (Official Gazette).")
    return " ".join(parts)
