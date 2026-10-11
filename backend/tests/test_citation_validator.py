"""Citation integrity: only verbatim source passages survive, pages come from the source."""
import pytest
from backend.app.config import settings

FRONT_ROW_3_6 = "More than 9.0 meters and up to 12 meters                    3.6 meters"
FARM_PLOT = "Minimum size of the plot shall be 0.40 hectare;"


def test_valid_citation_gets_source_page_and_title(citation_validator):
    validated = citation_validator.validate_citations(
        [{"rule_number": "17", "excerpt": FARM_PLOT, "document_title": "Some other title"}]
    )
    assert len(validated) == 1
    cit = validated[0]
    assert cit.rule_number == "17"
    assert cit.page_number == 34
    assert cit.document_title == settings.DOCUMENT_TITLE


def test_whitespace_case_and_dash_differences_are_tolerated(citation_validator):
    # Source: "1. Short title.—(1) These rules, may be called ..."
    validated = citation_validator.validate_citations(
        [{"rule_number": "1", "excerpt": "SHORT TITLE.-(1) These   rules, may be called the Madhya Pradesh Bhumi\nVikas Rules, 2012."}]
    )
    assert len(validated) == 1
    assert validated[0].page_number == 2


def test_table_row_with_collapsed_spacing_is_valid(citation_validator):
    validated = citation_validator.validate_citations([{"rule_number": "56", "excerpt": FRONT_ROW_3_6}])
    assert len(validated) == 1
    assert validated[0].page_number == 77


def test_hallucinated_rule_number_rejected(citation_validator):
    report = citation_validator.validate(
        [{"rule_number": "999", "excerpt": "All commercial buildings must provide helicopter parking pads."}]
    )
    assert report.citations == [] and report.rejected == 1


def test_fabricated_excerpt_in_real_rule_rejected(citation_validator):
    assert citation_validator.validate_citations(
        [{"rule_number": "56", "excerpt": "Residential houses may have zero setbacks if painted green."}]
    ) == []


def test_tampered_number_in_table_row_rejected(citation_validator):
    # Same words as the real row, wrong figure. A prefix-only check would accept this.
    tampered = "More than 9.0 meters and up to 12 meters 4.5 meters"
    assert citation_validator.validate_citations([{"rule_number": "56", "excerpt": tampered}]) == []


def test_real_prefix_with_fabricated_continuation_rejected(citation_validator):
    excerpt = FARM_PLOT + " and no permission is required for farm houses."
    assert citation_validator.validate_citations([{"rule_number": "17", "excerpt": excerpt}]) == []


def test_excerpt_attributed_to_wrong_rule_rejected(citation_validator):
    assert citation_validator.validate_citations([{"rule_number": "56", "excerpt": FARM_PLOT}]) == []


def test_missing_rule_number_resolved_when_excerpt_unique(citation_validator):
    validated = citation_validator.validate_citations([{"rule_number": None, "excerpt": FARM_PLOT}])
    assert len(validated) == 1 and validated[0].rule_number == "17"


def test_model_page_number_is_ignored(citation_validator):
    validated = citation_validator.validate_citations(
        [{"rule_number": "52", "page_number": 105, "excerpt": "Low and Medium voltage                         2.5                      1.2"}]
    )
    assert len(validated) == 1
    assert validated[0].page_number == 69


def test_page_resolved_within_multi_page_rule(citation_validator):
    validated = citation_validator.validate_citations(
        [{"rule_number": "56", "excerpt": "Above 40.00 and up to 150.00                            1.50"}]
    )
    assert validated[0].page_number == 78


def test_excerpt_across_page_break_reports_start_page(citation_validator):
    # "(6) Interior open spaces..." ends PDF page 78; "(a) Inner Courtyard" starts page 79.
    validated = citation_validator.validate_citations(
        [{"rule_number": "56", "excerpt": "Interior open spaces for all buildings,- (a) Inner Courtyard,-"}]
    )
    assert len(validated) == 1
    assert validated[0].page_number == 78


@pytest.mark.parametrize("excerpt", ["", "   ", "3.0 meters", "Rule 56"])
def test_trivial_excerpts_rejected(citation_validator, excerpt):
    assert citation_validator.validate_citations([{"rule_number": "56", "excerpt": excerpt}]) == []


def test_non_dict_entries_rejected(citation_validator):
    report = citation_validator.validate(["Rule 56", 42, None, ["x"]])
    assert report.citations == [] and report.rejected == 4


def test_duplicate_citations_deduplicated(citation_validator):
    raw = [{"rule_number": "17", "excerpt": FARM_PLOT}, {"rule_number": "17", "excerpt": FARM_PLOT.upper()}]
    assert len(citation_validator.validate_citations(raw)) == 1


def test_unsupported_numbers_detected(citation_validator):
    evidence = [FRONT_ROW_3_6]
    assert citation_validator.unsupported_numbers("The front open space is 3.6 meters.", evidence) == []
    assert citation_validator.unsupported_numbers("The front open space is 3.60 m.", evidence) == []
    assert citation_validator.unsupported_numbers("The front open space is 4.5 meters.", evidence) == [4.5]
    # Devanagari digits are normalized
    assert citation_validator.unsupported_numbers("न्यूनतम ३.६ मीटर", evidence) == []
