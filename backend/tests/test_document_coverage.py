"""Document coverage date and freshness notes."""
import pytest
from backend.app.models.schemas import ChatRequest
from backend.app.services import coverage
from backend.tests.conftest import llm_json

Q11 = ("Do I need separate development permission for a 300 sq m plot that matches the Development Plan? "
       "(Tip: this changed in August 2026.)")


@pytest.mark.asyncio
async def test_coverage_date_on_every_response(rag_service):
    for q in ["What is the distance required from overhead electric lines?",
              "How do I pay my property tax online?",
              "What is the cricket score today?"]:
        res = await rag_service.answer_question(ChatRequest(question=q))
        assert res.document_coverage_date == "2025-03-06"


@pytest.mark.asyncio
async def test_post_coverage_question_names_known_amendment(rag_service):
    res = await rag_service.answer_question(ChatRequest(question=Q11, language="en"))
    assert "2025-03-06" in res.answer
    assert "Rule 2(5)(c)" in res.answer and "2026-08-28" in res.answer


@pytest.mark.asyncio
async def test_post_coverage_note_survives_insufficient_evidence(scripted_rag):
    svc, _ = scripted_rag(llm_json("The supplied rules do not contain the August 2026 change.", insufficient=True))
    res = await svc.answer_question(ChatRequest(question=Q11))
    assert res.insufficient_evidence is True
    assert "Rule 2(5)(c)" in res.answer


@pytest.mark.asyncio
async def test_citing_amended_rule_adds_note(scripted_rag):
    excerpt = "the building permission shall be\nissued by the local bodies as per the landuse and landuse permissibility"
    svc, _ = scripted_rag(llm_json("In developed central areas, local bodies issue building permission.",
                                   [{"rule_number": "2", "excerpt": excerpt}]))
    res = await svc.answer_question(ChatRequest(
        question="Who issues building permission for land already developed in the Central area of the adopted Development Plan?"))
    assert res.citations and res.citations[0].rule_number == "2"
    assert "Rule 2(5)(c)" in res.answer


@pytest.mark.asyncio
async def test_no_note_for_ordinary_question(scripted_rag):
    svc, _ = scripted_rag(llm_json("Minimum plot size is 0.40 hectare.",
                                   [{"rule_number": "17", "excerpt": "Minimum size of the plot shall be 0.40 hectare;"}]))
    res = await svc.answer_question(ChatRequest(question="What is the minimum plot size for a farm house?"))
    assert "Note:" not in res.answer


@pytest.mark.asyncio
async def test_hindi_freshness_note(rag_service):
    res = await rag_service.answer_question(ChatRequest(question="2026 के नए संशोधन के बाद विकास अनुज्ञा के नियम क्या हैं?"))
    assert "सूचना" in res.answer


@pytest.mark.parametrize("question,expected", [
    ("What changed in August 2026?", True),
    ("Is this the latest rule?", True),
    ("My permission was granted in 2023.", False),
    ("What is the fee for 2025 applications?", False),
    ("Plot of 2026 sq m", True),  # conservative: any year-like number after 2025 triggers the note
])
def test_post_coverage_detection(question, expected):
    assert coverage.question_mentions_post_coverage(question) is expected
