"""Numerical requirements and exceptions: the right figures are retrieved, cited verbatim,
and figures the evidence does not support are flagged.

Expected figures were checked against data/bhumi_vikas_rules.jsonl (PDF pages noted).
"""
import pytest
from backend.app.models.schemas import ChatRequest
from backend.tests.conftest import llm_json

CASES = [
    # (question, rule, verbatim excerpt containing the figure, figure, PDF page)
    ("My house faces a 10 m wide street and will be 9 m tall. How much open space do I leave at the front?",
     "56", "More than 9.0 meters and up to 12 meters                    3.6 meters", "3.6 meters", 77),
    ("What is the minimum rear open space for a 150 sq m residential plot?",
     "56", "Above 40.00 and up to 150.00                            1.50", "1.50 meters", 78),
    ("I want a farm house on agricultural land. What is the minimum plot size and the maximum FAR?",
     "17", "Minimum size of the plot shall be 0.40 hectare;", "0.40 hectare", 34),
    ("How far must my balcony stay from a low-voltage overhead electric line, vertically and horizontally?",
     "52", "Low and Medium voltage                         2.5                      1.2", "2.5 m vertically and 1.2 m horizontally", 69),
    ("My development permission was granted in 2023. How long does it stay valid, and how many times can I renew it?",
     "23", "Such revalidation may be\npermitted for two consecutive terms of one year each", "two terms of one year each", 41),
]


@pytest.mark.parametrize("question,rule,excerpt,figure,page", CASES)
def test_figure_bearing_passage_is_retrieved(retriever, citation_validator, question, rule, excerpt, figure, page):
    results = retriever.retrieve(question, top_k=5)
    norm = citation_validator.normalize_text(excerpt)
    assert any(r.rule_number == rule and norm in citation_validator.normalize_text(r.text) for r in results)


@pytest.mark.asyncio
@pytest.mark.parametrize("question,rule,excerpt,figure,page", CASES)
async def test_grounded_numeric_answer_passes(scripted_rag, question, rule, excerpt, figure, page):
    svc, _ = scripted_rag(llm_json(f"Under Rule {rule} the requirement is {figure}.",
                                   [{"rule_number": rule, "excerpt": excerpt}]))
    res = await svc.answer_question(ChatRequest(question=question, language="en"))
    assert res.insufficient_evidence is False
    assert res.citations[0].rule_number == rule
    assert res.citations[0].page_number == page
    assert "Caution" not in res.answer


@pytest.mark.asyncio
async def test_wrong_figure_in_answer_is_flagged(scripted_rag):
    # The model cites the real 3.6 m row but states 4.5 m in its answer.
    svc, _ = scripted_rag(llm_json(
        "The front open space must be 4.5 meters.",
        [{"rule_number": "56", "excerpt": "More than 9.0 meters and up to 12 meters 3.6 meters"}],
    ))
    res = await svc.answer_question(ChatRequest(
        question="My house faces a 10 m wide street and will be 9 m tall. How much open space do I leave at the front?"))
    assert res.confidence.value == "low"
    assert "Caution" in res.answer and "4.5" in res.answer


@pytest.mark.asyncio
async def test_tampered_figure_in_citation_is_dropped(scripted_rag):
    svc, _ = scripted_rag(llm_json(
        "The front open space must be 4.5 meters.",
        [{"rule_number": "56", "excerpt": "More than 9.0 meters and up to 12 meters 4.5 meters"}],
    ))
    res = await svc.answer_question(ChatRequest(question="Front open space for a house on a 10 m wide street?"))
    assert res.insufficient_evidence is True
    assert res.citations == []


def test_exception_proviso_is_retrievable(retriever):
    # Rule 56(3)(i) proviso: one side open space may be reduced to 1.5 m on narrow plots.
    results = retriever.retrieve(
        "Can the side open space be reduced for a detached house on a plot with frontage less than 12 meters?", top_k=5)
    assert any(r.rule_number == "56" and "may be reduced to 1.5 meters" in " ".join(r.text.split()) for r in results)


@pytest.mark.asyncio
async def test_partial_citation_rejection_caps_confidence(scripted_rag):
    svc, _ = scripted_rag(llm_json(
        "Minimum plot 0.40 hectare and maximum FAR 0.10.",
        [{"rule_number": "17", "excerpt": "Minimum size of the plot shall be 0.40 hectare;"},
         {"rule_number": "17", "excerpt": "Maximum F.A.R. shall be 0.10;"},
         {"rule_number": "17", "excerpt": "Farm houses are exempt from all permission requirements."}],
    ))
    res = await svc.answer_question(ChatRequest(
        question="I want a farm house on agricultural land. What is the minimum plot size and the maximum FAR?"))
    assert len(res.citations) == 2
    assert res.confidence.value == "medium"
