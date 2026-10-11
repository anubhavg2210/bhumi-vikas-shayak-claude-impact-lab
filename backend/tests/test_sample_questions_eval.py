"""Benchmark over data/resources/sample_questions.md.

The expected rule for each question was identified by reading the rule text in
data/bhumi_vikas_rules.jsonl; question 11 has no expected rule because the relevant
change (August 2026) is outside the collection.
"""
import re
from pathlib import Path
import pytest
from backend.app.models.schemas import ChatRequest

SAMPLE_FILE = Path(__file__).resolve().parents[2] / "data" / "resources" / "sample_questions.md"

EXPECTED_RULE = {
    1: "56",    # front open space table
    2: "17",    # farm house
    3: "23",    # duration of sanction / revalidation
    4: "28",    # limitation period, deemed sanction
    5: "52",    # distance from electric lines
    6: "18",    # preparation and signing of plans
    7: "16",    # information accompanying application
    8: "21",    # fees
    9: "24",    # deviation from sanctioned plan
    10: "56",   # rear open space table
    12: "103",  # development plan takes precedence
    13: "83",   # lifts
    14: "56",   # (Hindi) front open space
    15: "21",   # (Hindi) fees
}
OUT_OF_SCOPE = {16, 17}


def _load_questions():
    questions = {}
    for line in SAMPLE_FILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if m:
            questions[int(m.group(1))] = m.group(2).strip()
    return questions


QUESTIONS = _load_questions()


def test_sample_file_has_17_questions():
    assert sorted(QUESTIONS) == list(range(1, 18))


@pytest.mark.parametrize("num", sorted(EXPECTED_RULE))
def test_expected_rule_retrieved_in_top_5(retriever, num):
    results = retriever.retrieve(QUESTIONS[num], top_k=5)
    assert EXPECTED_RULE[num] in [r.rule_number for r in results]


def test_top_1_accuracy(retriever):
    hits = sum(retriever.retrieve(QUESTIONS[n], top_k=1)[0].rule_number == rule for n, rule in EXPECTED_RULE.items())
    # Measured 13/14 when written (Q14, Hindi, ranks Rule 57 first); guard against regressions.
    assert hits >= 13


@pytest.mark.asyncio
@pytest.mark.parametrize("num", sorted(EXPECTED_RULE))
async def test_extractive_answers_cite_expected_rule(rag_service, num):
    res = await rag_service.answer_question(ChatRequest(question=QUESTIONS[num]))
    assert res.insufficient_evidence is False
    assert EXPECTED_RULE[num] in [c.rule_number for c in res.citations]
    assert all(c.page_number is not None for c in res.citations)


@pytest.mark.asyncio
@pytest.mark.parametrize("num", sorted(OUT_OF_SCOPE))
async def test_out_of_scope_questions_not_found(rag_service, num):
    res = await rag_service.answer_question(ChatRequest(question=QUESTIONS[num]))
    assert res.insufficient_evidence is True
    assert res.citations == []


@pytest.mark.asyncio
async def test_question_11_flags_post_coverage_change(rag_service):
    res = await rag_service.answer_question(ChatRequest(question=QUESTIONS[11]))
    assert "Rule 2(5)(c)" in res.answer
