"""Semantic retrieval over rag/knowledge_base/ markdown documents.

Uses api-tgpt-embeddings (TritonAI) + cosine similarity.
Index is built on first call and cached to rag/index/embedding_index.json.

Run directly to rebuild the index and test sample queries::

    uv run python rag/retrieval.py
"""

from __future__ import annotations

import json
import math
import os
import re
import string
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

KB_DIR = Path(__file__).resolve().parent / "knowledge_base"
INDEX_DIR = Path(__file__).resolve().parent / "index"
INDEX_PATH = INDEX_DIR / "embedding_index.json"

EMBED_MODEL = "api-tgpt-embeddings"
TRITONAI_BASE = "https://tritonai-api.ucsd.edu/v1"


# ── document parsing ──────────────────────────────────────────────────────────

def _parse_frontmatter(content: str) -> tuple[dict, str]:
    meta: dict[str, str] = {}
    if not content.startswith("---"):
        return meta, content
    end = content.find("---", 3)
    if end == -1:
        return meta, content
    for line in content[3:end].strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, content[end + 3:].strip()


def _chunk_document(doc_id: str, meta: dict, body: str) -> list[dict]:
    title = meta.get("title", doc_id)
    chunks = []
    for i, section in enumerate(re.split(r"\n##\s+", body)):
        lines = section.strip().splitlines()
        if not lines:
            continue
        heading = lines[0].strip("# ").strip()
        text = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        if not text:
            continue
        chunks.append({
            "doc_id": doc_id,
            "title": title,
            "section": heading,
            "snippet": text[:300].replace("\n", " ").strip(),
        })
    return chunks


def _load_all_chunks() -> list[dict]:
    chunks: list[dict] = []
    for md_file in sorted(KB_DIR.glob("*.md")):
        if md_file.name == "EXAMPLE.md":
            continue
        doc_id = md_file.stem.upper().replace("-", "_")
        content = md_file.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(content)
        chunks.extend(_chunk_document(doc_id, meta, body))
    return chunks


# ── embedding helpers ─────────────────────────────────────────────────────────

def _get_client():
    from openai import OpenAI
    key = os.environ.get("TRITONAI_API_KEY", "")
    if not key:
        raise RuntimeError("TRITONAI_API_KEY is not set — copy .env.example to .env and fill in your key.")
    return OpenAI(api_key=key, base_url=TRITONAI_BASE)


def _embed(texts: list[str]) -> list[list[float]]:
    response = _get_client().embeddings.create(input=texts, model=EMBED_MODEL)
    return [item.embedding for item in response.data]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


# ── index ─────────────────────────────────────────────────────────────────────

def build_index() -> list[dict]:
    """Embed all KB chunks and cache to INDEX_PATH. Returns chunk list."""
    INDEX_DIR.mkdir(exist_ok=True)
    chunks = _load_all_chunks()
    if not chunks:
        INDEX_PATH.write_text(json.dumps({"model": EMBED_MODEL, "chunks": []}))
        return []

    texts = [f"{c['section']}: {c['snippet']}" for c in chunks]
    embeddings = _embed(texts)

    index_data = {
        "model": EMBED_MODEL,
        "chunks": [
            {**c, "embedding": emb}
            for c, emb in zip(chunks, embeddings)
        ],
    }
    INDEX_PATH.write_text(json.dumps(index_data), encoding="utf-8")
    print(f"[rag] {len(chunks)} chunks indexed → {INDEX_PATH}")
    return chunks


def _load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        build_index()
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return data["chunks"]


# ── public API ────────────────────────────────────────────────────────────────

def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Return up to top_k chunks most relevant to query.

    Each result dict contains: doc_id, title, section, snippet, score
    Returns [] when query is empty.
    """
    if not query or not query.strip():
        return []

    chunks = _load_index()
    if not chunks:
        return []

    q_vec = _embed([query])[0]

    scored = sorted(
        [(_cosine(q_vec, c["embedding"]), c) for c in chunks],
        key=lambda x: x[0],
        reverse=True,
    )

    return [
        {
            "doc_id": c["doc_id"],
            "title": c["title"],
            "section": c["section"],
            "snippet": c["snippet"],
            "score": round(score, 4),
        }
        for score, c in scored[:top_k]
    ]


if __name__ == "__main__":
    print("Building index...")
    build_index()

    test_queries = [
        "outreach tone guidelines nano creators banned phrases",
        "affiliate commission rate promo code format",
        "brand safety RED AMBER GREEN flagged comments",
        "Lululemon competitor conflict of interest",
        "product brief key message must include",
    ]
    print("\nTest queries:")
    for q in test_queries:
        results = retrieve(q, top_k=2)
        print(f"\nQuery: {q!r}")
        for r in results:
            print(f"  [{r['score']:.4f}] {r['title']} › {r['section']}")
            print(f"           {r['snippet'][:100]}...")
