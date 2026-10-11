"""Hindi questions: language detection, Hindi answers, and cross-lingual retrieval."""
import pytest
from backend.app.models.schemas import ChatRequest
from backend.tests.conftest import llm_json

Q14_HI = "मेरा प्लॉट 200 वर्ग मीटर का है और सामने 9 मीटर चौड़ी सड़क है। आगे कितनी जगह खाली छोड़नी होगी?"


def _has_devanagari(text):
    return any(0x0900 <= ord(c) <= 0x097F for c in text)


@pytest.mark.asyncio
async def test_hindi_question_with_scripted_hindi_answer(scripted_rag):
    svc, provider = scripted_rag(llm_json(
        "नियम 56(1)(a) के अनुसार 9.0 मीटर तक चौड़ी सड़क के लिए न्यूनतम अग्र खुला स्थान 3.0 मीटर है।",
        [{"rule_number": "56", "excerpt": "Up to 9.0 meters                                            3.0 meters"}],
    ))
    res = await svc.answer_question(ChatRequest(question=Q14_HI, language="hi"))
    assert res.language == "hi"
    assert res.insufficient_evidence is False
    assert res.citations[0].rule_number == "56" and res.citations[0].page_number == 77
    assert "Caution" not in res.answer and "सावधानी" not in res.answer
    assert "Requested answer language: Hindi" in provider.calls[0]["user"]


@pytest.mark.asyncio
async def test_language_autodetected_from_devanagari(rag_service):
    res = await rag_service.answer_question(ChatRequest(question="बिल्डिंग परमिशन की फीस किस नियम में है?"))
    assert res.language == "hi"
    assert _has_devanagari(res.answer)


@pytest.mark.asyncio
async def test_explicit_language_overrides_detection(rag_service):
    res = await rag_service.answer_question(ChatRequest(question="What is the fee for building permission?", language="hi"))
    assert res.language == "hi"
    assert _has_devanagari(res.answer)


@pytest.mark.asyncio
async def test_hindi_extractive_answer_cites_english_source(rag_service):
    res = await rag_service.answer_question(ChatRequest(question="बिल्डिंग परमिशन की फीस कितनी है और किस नियम में लिखी है?"))
    assert res.insufficient_evidence is False
    assert any(c.rule_number == "21" for c in res.citations)
    assert _has_devanagari(res.answer)


@pytest.mark.asyncio
async def test_hindi_out_of_scope(rag_service):
    res = await rag_service.answer_question(ChatRequest(question="मेरी संपत्ति कर ऑनलाइन कैसे जमा करें?"))
    assert res.language == "hi" and res.insufficient_evidence is True
    assert _has_devanagari(res.answer)
