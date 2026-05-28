"""Tests for rag/retrieval.py — embedding-based semantic search over the knowledge base."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.retrieval import (
    _chunk_document,
    _parse_frontmatter,
    build_index,
    retrieve,
)


# ── frontmatter parser ────────────────────────────────────────────────────────

def test_parse_frontmatter_extracts_title():
    content = "---\ntitle: My Doc\ncategory: Test\n---\n\nBody text here."
    meta, body = _parse_frontmatter(content)
    assert meta["title"] == "My Doc"
    assert meta["category"] == "Test"
    assert "Body text here." in body

def test_parse_frontmatter_no_frontmatter():
    content = "# Just a heading\nSome body."
    meta, body = _parse_frontmatter(content)
    assert meta == {}
    assert "Just a heading" in body

def test_parse_frontmatter_missing_closing_dashes():
    content = "---\ntitle: Broken\nNo closing dashes, just body."
    meta, body = _parse_frontmatter(content)
    assert meta == {}


# ── chunker ───────────────────────────────────────────────────────────────────

def test_chunk_document_splits_on_headings():
    body = "# Intro\nIntro text.\n\n## Section One\nContent one.\n\n## Section Two\nContent two."
    chunks = _chunk_document("TEST_DOC", {"title": "Test"}, body)
    sections = [c["section"] for c in chunks]
    assert any("Section One" in s for s in sections)
    assert any("Section Two" in s for s in sections)

def test_chunk_document_sets_doc_id_and_title():
    body = "## Only Section\nContent here."
    chunks = _chunk_document("MY_DOC", {"title": "My Title"}, body)
    assert chunks[0]["doc_id"] == "MY_DOC"
    assert chunks[0]["title"] == "My Title"

def test_chunk_document_empty_body():
    chunks = _chunk_document("EMPTY", {}, "")
    assert chunks == []

def test_chunk_document_skips_headeronly_sections():
    # A section with only a heading line and no body should be skipped
    body = "# Doc Title\n\n## Real Section\nActual content here."
    chunks = _chunk_document("DOC", {"title": "Doc"}, body)
    sections = [c["section"] for c in chunks]
    assert "Doc Title" not in sections
    assert "Real Section" in sections

def test_chunk_snippet_truncated_to_300():
    long_text = "## Big Section\n" + "word " * 200
    chunks = _chunk_document("LONG", {"title": "Long"}, long_text)
    assert len(chunks[0]["snippet"]) <= 300


# ── retrieve — happy path ────────────────────────────────────────────────────

def test_retrieve_returns_list():
    results = retrieve("affiliate commission rate promo code")
    assert isinstance(results, list)

def test_retrieve_top_k_respected():
    results = retrieve("creator outreach tone guidelines", top_k=2)
    assert len(results) <= 2

def test_retrieve_result_has_required_keys():
    results = retrieve("brand safety RED AMBER GREEN", top_k=1)
    assert len(results) >= 1
    r = results[0]
    assert "doc_id" in r
    assert "title" in r
    assert "section" in r
    assert "snippet" in r
    assert "score" in r

def test_retrieve_score_between_0_and_1():
    results = retrieve("Lululemon competitor conflict", top_k=3)
    for r in results:
        assert 0 < r["score"] <= 1.0

def test_retrieve_competitor_query_hits_competitor_doc():
    results = retrieve("Lululemon Fabletics direct competitor do not partner", top_k=2)
    assert results, "Expected at least one result"
    doc_ids = {r["doc_id"] for r in results}
    assert any("COMPETITOR" in d or "SAFETY" in d or "AUDIENCE" in d for d in doc_ids)

def test_retrieve_commission_query_hits_affiliate_doc():
    results = retrieve("affiliate commission rate 12 percent promo code format", top_k=1)
    assert results, "Expected at least one result"
    assert "AFFILIATE" in results[0]["doc_id"] or "DEAL" in results[0]["doc_id"]

def test_retrieve_brand_safety_query_hits_safety_doc():
    results = retrieve("brand safety flagged comments toxicity RED AMBER", top_k=1)
    assert results, "Expected at least one result"
    assert "SAFETY" in results[0]["doc_id"] or "AUDIENCE" in results[0]["doc_id"]

def test_retrieve_results_sorted_by_score_descending():
    results = retrieve("outreach message tone nano micro creator", top_k=5)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


# ── retrieve — edge cases ─────────────────────────────────────────────────────

def test_retrieve_empty_query_returns_empty():
    assert retrieve("") == []

def test_retrieve_whitespace_only_returns_empty():
    assert retrieve("   ") == []

def test_retrieve_top_k_zero_returns_empty():
    results = retrieve("commission rate", top_k=0)
    assert results == []


# ── index on disk ─────────────────────────────────────────────────────────────

def test_build_index_creates_json_file():
    index_path = ROOT / "rag" / "index" / "embedding_index.json"
    build_index()
    assert index_path.exists()
    data = json.loads(index_path.read_text())
    assert "chunks" in data
    assert "model" in data
    assert len(data["chunks"]) > 0

def test_index_chunk_has_embedding():
    index_path = ROOT / "rag" / "index" / "embedding_index.json"
    build_index()
    data = json.loads(index_path.read_text())
    chunk = data["chunks"][0]
    assert "embedding" in chunk
    assert isinstance(chunk["embedding"], list)
    assert len(chunk["embedding"]) > 0

def test_index_covers_all_kb_documents():
    index_path = ROOT / "rag" / "index" / "embedding_index.json"
    build_index()
    data = json.loads(index_path.read_text())
    doc_ids = {c["doc_id"] for c in data["chunks"]}
    assert len(doc_ids) == 10
