"""Ingestion: rule records, page index, and chunk integrity."""
from backend.app.services.document_store import DocumentStore, PAGE_HEADER_RE, normalize_text


def test_all_rules_loaded(doc_store):
    rules = doc_store.get_all_rules()
    assert len(rules) == 106
    assert doc_store.get_rule("26-B") is not None
    assert doc_store.get_rule("26-b") is not None
    assert doc_store.get_rule("106") is None


def test_page_index_loaded(doc_store):
    assert len(doc_store.normalized_pages) == 108
    assert "front open space min" in doc_store.normalized_pages[77]


def test_page_headers_are_stripped_from_page_index(doc_store):
    assert "m.p. bhumi vikas rules, 2012 78" not in doc_store.normalized_pages[78]


def test_chunk_pages_are_within_rule_range(doc_store):
    for chunk in doc_store.get_all_chunks():
        rule = doc_store.get_rule(chunk.rule_number)
        assert rule.page_start <= chunk.page_number <= rule.page_end, chunk.chunk_id


def test_chunks_contain_no_running_headers(doc_store):
    for chunk in doc_store.get_all_chunks():
        assert not PAGE_HEADER_RE.search(chunk.text), chunk.chunk_id


def test_every_chunk_is_verbatim_rule_text(doc_store):
    for chunk in doc_store.get_all_chunks():
        rule = doc_store.get_rule(chunk.rule_number)
        assert normalize_text(chunk.text) in rule.normalized_text, chunk.chunk_id


def test_table_header_kept_with_rows(doc_store):
    chunk = next(c for c in doc_store.get_rule("56").chunks if "3.6 meters" in c.text)
    assert "Width of street facing the plot" in chunk.text


def test_missing_data_file_gives_empty_store(tmp_path):
    store = DocumentStore(data_file_path=tmp_path / "missing.jsonl")
    assert store.get_all_rules() == []
    assert store.get_all_chunks() == []


def test_malformed_lines_are_skipped(tmp_path):
    path = tmp_path / "rules.jsonl"
    path.write_text(
        '{"rule": "1", "title": "Short title", "part": "Part I", "page_start": 2, "page_end": 2, "text": "1. Short title.- These rules may be called the test rules."}\n'
        "not json\n"
        '{"title": "no rule number"}\n',
        encoding="utf-8",
    )
    store = DocumentStore(data_file_path=path)
    assert [r.rule_number for r in store.get_all_rules()] == ["1"]
