"""ChromaDB + SentenceTransformer retrieval backend for CrystalPilot RAG.

Documents in ``_KNOWLEDGE_DIR`` are chunked with heading-aware splitting and
indexed in a persistent ChromaDB collection using sentence-transformer
embeddings.  The embedding model is lazy-loaded to avoid blocking app startup.

Falls back to TF-IDF retrieval if ChromaDB or sentence-transformers are not
installed, so the agent can still work without the heavier dependencies.

Usage::

    kb = BeamlineKnowledgeBase()
    passages = kb.retrieve("what is the TOPAZ wavelength range", k=3)
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
_CHROMA_DIR = _KNOWLEDGE_DIR / "chroma_db"
_COLLECTION_NAME = "crystalpilot_docs"
_CHUNK_SIZE = 150    # words per chunk
_OVERLAP = 25        # word overlap between adjacent chunks
_DEFAULT_K = 3       # passages returned by default


# ---------------------------------------------------------------------------
# Chunking helpers (heading-aware, then word-window)
# ---------------------------------------------------------------------------

def _load_and_chunk(knowledge_dir: Path) -> tuple[list[str], list[dict]]:
    """Load all .md and .txt files and return (texts, metadatas)."""
    chunks: list[str] = []
    metas: list[dict] = []
    patterns = ("**/*.md", "**/*.txt")
    found: list[Path] = []
    for pat in patterns:
        found.extend(sorted(knowledge_dir.glob(pat)))
    for fpath in found:
        if "chroma_db" in str(fpath):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            logger.warning("RAG: could not read %s", fpath)
            continue
        for chunk in _chunk_text(text, fpath.name):
            chunks.append(chunk)
            metas.append({"source": fpath.name})
    return chunks, metas


def _chunk_text(text: str, source: str) -> list[str]:
    """Split *text* into semantically coherent chunks, tagged with *source*.

    Strategy (heading-aware, then word-window):
    1. Split on ``## `` boundaries so each Markdown section stays together.
    2. Any section that exceeds *_CHUNK_SIZE* words is further split into
       overlapping word-windows.
    """
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
            j = 0
            while j < len(words):
                snippet = " ".join(words[j : j + _CHUNK_SIZE])
                result.append(f"[{source}]\n{snippet}")
                j += _CHUNK_SIZE - _OVERLAP
    return result


def _content_hash(chunks: list[str]) -> str:
    """Compute a hash of all chunk contents to detect changes."""
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.encode("utf-8"))
    return h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Embedding function with lazy model loading
# ---------------------------------------------------------------------------

class _LazyEmbeddingFunction:
    """ChromaDB-compatible embedding function with lazy SentenceTransformer loading."""

    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model (first use)…")
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer model loaded.")
        return cls._model

    def __call__(self, input: list[str]) -> list[list[float]]:
        model = self._get_model()
        return model.encode(input).tolist()


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

class BeamlineKnowledgeBase:
    """Semantic retriever over local knowledge files.

    Uses ChromaDB with SentenceTransformer embeddings if available,
    falls back to TF-IDF (scikit-learn) otherwise.

    Parameters
    ----------
    knowledge_dir:
        Directory containing ``.md`` / ``.txt`` knowledge documents.
        Defaults to ``src/exphub/agent/knowledge/``.
    """

    def __init__(self, knowledge_dir: Path = _KNOWLEDGE_DIR) -> None:
        self._chunks: list[str] = []
        self._collection = None
        self._fallback_vectorizer = None
        self._fallback_matrix = None

        texts, metas = _load_and_chunk(knowledge_dir)
        self._chunks = texts

        if not texts:
            logger.warning("RAG: no documents found in %s", knowledge_dir)
            return

        # Try ChromaDB first, fall back to TF-IDF
        if self._try_chromadb(texts, metas, knowledge_dir):
            logger.info("RAG: using ChromaDB with %d chunks", len(texts))
        else:
            self._build_tfidf_index(texts)
            logger.info("RAG: using TF-IDF fallback with %d chunks", len(texts))

    def _try_chromadb(self, texts: list[str], metas: list[dict], knowledge_dir: Path) -> bool:
        """Attempt to initialise ChromaDB collection. Returns True on success."""
        try:
            import chromadb
        except ImportError:
            logger.info("RAG: chromadb not installed — using TF-IDF fallback")
            return False

        try:
            chroma_dir = knowledge_dir / "chroma_db"
            chroma_dir.mkdir(exist_ok=True)
            client = chromadb.PersistentClient(path=str(chroma_dir))
            embedding_fn = _LazyEmbeddingFunction()

            content_hash = _content_hash(texts)

            # Check if collection already exists and is up to date
            try:
                collection = client.get_collection(
                    _COLLECTION_NAME, embedding_function=embedding_fn
                )
                stored_hash = collection.metadata.get("content_hash", "")
                if stored_hash == content_hash and collection.count() == len(texts):
                    self._collection = collection
                    return True
                # Content changed — rebuild
                client.delete_collection(_COLLECTION_NAME)
            except Exception:
                pass  # Collection doesn't exist yet

            # Create and populate
            collection = client.create_collection(
                _COLLECTION_NAME,
                embedding_function=embedding_fn,
                metadata={"content_hash": content_hash},
            )
            ids = [f"chunk_{i}" for i in range(len(texts))]
            # ChromaDB has a batch limit; add in batches of 500
            batch_size = 500
            for start in range(0, len(texts), batch_size):
                end = min(start + batch_size, len(texts))
                collection.add(
                    ids=ids[start:end],
                    documents=texts[start:end],
                    metadatas=metas[start:end],
                )
            self._collection = collection
            return True

        except Exception as exc:
            logger.warning("RAG: ChromaDB init failed (%s) — using TF-IDF fallback", exc)
            return False

    def _build_tfidf_index(self, texts: list[str]) -> None:
        """Build a TF-IDF index as fallback."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._fallback_vectorizer = TfidfVectorizer(
                stop_words="english", max_features=30_000, ngram_range=(1, 2),
            )
            self._fallback_matrix = self._fallback_vectorizer.fit_transform(texts)
        except ImportError:
            logger.warning("RAG: neither chromadb nor scikit-learn installed — RAG disabled")

    def retrieve(self, query: str, k: int = _DEFAULT_K) -> list[str]:
        """Return up to *k* passages most relevant to *query*."""
        if self._collection is not None:
            return self._retrieve_chromadb(query, k)
        if self._fallback_vectorizer is not None:
            return self._retrieve_tfidf(query, k)
        return []

    def _retrieve_chromadb(self, query: str, k: int) -> list[str]:
        """Retrieve using ChromaDB semantic search."""
        try:
            results = self._collection.query(query_texts=[query], n_results=k)
            docs = results.get("documents", [[]])[0]
            return [d for d in docs if d]
        except Exception as exc:
            logger.warning("RAG: ChromaDB query failed (%s)", exc)
            return []

    def _retrieve_tfidf(self, query: str, k: int) -> list[str]:
        """Retrieve using TF-IDF cosine similarity (fallback)."""
        from sklearn.metrics.pairwise import cosine_similarity
        q_vec = self._fallback_vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self._fallback_matrix).flatten()
        n = min(k, len(scores))
        top_idx = scores.argsort()[-n:][::-1]
        return [self._chunks[i] for i in top_idx if scores[i] > 1e-6]

    @property
    def document_count(self) -> int:
        """Number of indexed chunks."""
        return len(self._chunks)
