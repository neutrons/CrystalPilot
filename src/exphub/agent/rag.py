"""Lightweight TF-IDF retrieval backend for the CrystalPilot RAG tool.

Documents in ``_KNOWLEDGE_DIR`` are chunked once at init time and indexed
with scikit-learn's TfidfVectorizer.  No external services or vector-store
libraries are required — scikit-learn is already a project dependency.

Usage::

    kb = BeamlineKnowledgeBase()
    passages = kb.retrieve("what is the TOPAZ wavelength range", k=3)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
_CHUNK_SIZE = 150    # words per chunk
_OVERLAP = 25        # word overlap between adjacent chunks
_DEFAULT_K = 3       # passages returned by default


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_documents(knowledge_dir: Path) -> list[str]:
    """Load all .md and .txt files from *knowledge_dir* and its subdirs."""
    chunks: list[str] = []
    patterns = ("**/*.md", "**/*.txt")
    found: list[Path] = []
    for pat in patterns:
        found.extend(sorted(knowledge_dir.glob(pat)))
    for fpath in found:
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            logger.warning("RAG: could not read %s", fpath)
            continue
        file_chunks = _chunk_text(text, fpath.name)
        chunks.extend(file_chunks)
    return chunks


def _chunk_text(text: str, source: str) -> list[str]:
    """Split *text* into semantically coherent chunks, tagged with *source*.

    Strategy (heading-aware, then word-window):
    1. Split on ``## `` boundaries so each Markdown section stays together.
    2. Any section that exceeds *_CHUNK_SIZE* words is further split into
       overlapping word-windows (same overlap as before).
    This keeps related content in one chunk and avoids cutting mid-sentence.
    """
    # Split into sections on level-2 headings; re-attach the heading marker.
    raw_sections: list[str] = []
    for i, part in enumerate(text.split("\n## ")):
        raw_sections.append(part if i == 0 else "## " + part)

    result: list[str] = []
    for section in raw_sections:
        section = section.strip()
        if not section:
            continue
        words = section.split()
        if len(words) <= _CHUNK_SIZE:
            result.append(f"[{source}]\n{section}")
        else:
            # Sub-chunk large sections with overlap
            i = 0
            while i < len(words):
                snippet = " ".join(words[i : i + _CHUNK_SIZE])
                result.append(f"[{source}]\n{snippet}")
                i += _CHUNK_SIZE - _OVERLAP
    return result


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

class BeamlineKnowledgeBase:
    """TF-IDF semantic retriever over local knowledge files.

    Parameters
    ----------
    knowledge_dir:
        Directory containing ``.md`` / ``.txt`` knowledge documents.
        Defaults to ``src/exphub/agent/knowledge/``.
    """

    def __init__(self, knowledge_dir: Path = _KNOWLEDGE_DIR) -> None:
        self._chunks: list[str] = _load_documents(knowledge_dir)
        self._vectorizer = None
        self._matrix = None

        if self._chunks:
            self._build_index()
        else:
            logger.warning(
                "RAG: no documents found in %s — retrieve_docs will be a no-op",
                knowledge_dir,
            )

    def _build_index(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer  # lazy import

        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=30_000,
            ngram_range=(1, 2),
        )
        self._matrix = self._vectorizer.fit_transform(self._chunks)
        logger.info(
            "RAG: indexed %d chunks from %s",
            len(self._chunks),
            _KNOWLEDGE_DIR,
        )

    def retrieve(self, query: str, k: int = _DEFAULT_K) -> list[str]:
        """Return up to *k* passages most relevant to *query*.

        Returns an empty list when no documents are indexed.
        """
        if self._vectorizer is None or self._matrix is None:
            return []
        from sklearn.metrics.pairwise import cosine_similarity  # lazy import

        q_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._matrix).flatten()
        n = min(k, len(scores))
        top_idx = scores.argsort()[-n:][::-1]
        return [self._chunks[i] for i in top_idx if scores[i] > 1e-6]

    @property
    def document_count(self) -> int:
        """Number of indexed chunks."""
        return len(self._chunks)
