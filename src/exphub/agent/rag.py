"""ChromaDB + SentenceTransformer retrieval backend for CrystalPilot RAG.

Documents in ``_KNOWLEDGE_DIR`` are chunked with heading-aware splitting and
indexed in a persistent ChromaDB collection using sentence-transformer
embeddings.  The embedding model is lazy-loaded to avoid blocking app startup.

Falls back to TF-IDF retrieval if ChromaDB or sentence-transformers are not
installed, so the agent can still work without the heavier dependencies.

Usage::

    kb = BeamlineKnowledgeBase()
    passages = kb.retrieve("what is the wavelength range")
    answer  = kb.answer("what is the wavelength range")  # synthesised
"""

from __future__ import annotations

import hashlib
import importlib
import logging
import math
import re
from pathlib import Path
from typing import Any, Sequence, cast

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
_CHROMA_DIR = _KNOWLEDGE_DIR / "chroma_db"
_COLLECTION_NAME = "crystalpilot_docs"
_CHUNK_SIZE = 150    # words per chunk
_OVERLAP = 25        # word overlap between adjacent chunks
_DEFAULT_K = 3       # passages returned by default
_RERANK_K = 60       # candidates fetched for reranking
_CONTEXT_TOKEN_LIMIT = 3000  # max tokens fed to the synthesis LLM


# ---------------------------------------------------------------------------
# Keyword scoring (BM25-ish boost for reranking)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset(
    {"the", "a", "an", "of", "in", "on", "at", "to", "by", "for",
     "with", "and", "or", "from", "is", "it", "this", "that", "are"}
)


def _keyword_score(query: str, text: str) -> float:
    """Return a BM25-ish keyword overlap score between *query* and *text*."""
    q_words = [w for w in re.findall(r"\w+", query.lower()) if w not in _STOP_WORDS]
    d_words = re.findall(r"\w+", text.lower())
    if not d_words:
        return 0.0
    overlap = len(set(q_words) & set(d_words))
    return overlap / (1.0 + math.log2(len(d_words)))


def _estimate_tokens(text: str) -> int:
    """Rough token count (words * 1.3)."""
    return int(len(text.split()) * 1.3)


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

    _model: Any = None

    @classmethod
    def _get_model(cls) -> Any:
        if cls._model is None:
            SentenceTransformer = importlib.import_module(
                "sentence_transformers"
            ).SentenceTransformer
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
        self._collection: Any = None
        self._fallback_vectorizer: Any = None
        self._fallback_matrix: Any = None

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
            chromadb = importlib.import_module("chromadb")
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
        """Return up to *k* passages most relevant to *query*.

        When ChromaDB is available, fetches many candidates and reranks with
        keyword boosting before returning the top *k*.
        """
        if self._collection is not None:
            return self._retrieve_chromadb(query, k)
        if self._fallback_vectorizer is not None:
            return self._retrieve_tfidf(query, k)
        return []

    def retrieve_with_budget(self, query: str, token_limit: int = _CONTEXT_TOKEN_LIMIT) -> list[str]:
        """Retrieve passages up to *token_limit* tokens, using keyword-boosted reranking.

        Fetches a large candidate set, reranks by keyword overlap, and
        accumulates passages until the token budget is exhausted.
        """
        if self._collection is not None:
            return self._retrieve_chromadb_reranked(query, token_limit)
        # Fallback: use basic TF-IDF retrieval
        if self._fallback_vectorizer is not None:
            return self._retrieve_tfidf(query, k=10)
        return []

    def answer(self, query: str) -> str:
        """Retrieve relevant passages and synthesise a direct answer via LLM.

        Uses keyword-boosted reranking to select context, then calls the
        configured LLM to produce a concise answer grounded in the passages.
        Returns the synthesised answer string, or a fallback message.
        """
        passages = self.retrieve_with_budget(query)
        if not passages:
            logger.info("RAG: no passages found for query: %s", query)
            return "No relevant documentation found for that query."

        logger.info("RAG: found %d passages for query: %s", len(passages), query)
        context = "\n\n---\n\n".join(passages)
        prompt = (
            "You are CrystalPilot Assistant. Answer the QUESTION using ONLY "
            "the CONTEXT below. Be concise, accurate, and use Markdown.\n\n"
            f"QUESTION:\n{query}\n\n"
            f"CONTEXT:\n{context}\n\n"
            "ANSWER:"
        )

        try:
            from .llm import get_configured_chat_model
            llm = get_configured_chat_model()
            logger.info("RAG: calling synthesis LLM…")
            result = llm.invoke(prompt)
            answer = (
                cast(str, result.content).strip()
                if hasattr(result, "content")
                else str(result).strip()
            )
            logger.info("RAG: synthesis answer (first 120 chars): %s", answer[:120])
            return answer
        except Exception as exc:
            logger.warning("RAG: synthesis LLM call failed (%s) — returning raw passages", exc)
            return context

    def _retrieve_chromadb(self, query: str, k: int) -> list[str]:
        """Retrieve using ChromaDB with keyword-boosted reranking."""
        try:
            # Fetch a large candidate set for reranking
            fetch_k = max(k, _RERANK_K)
            results = self._collection.query(query_texts=[query], n_results=fetch_k)
            docs = results.get("documents", [[]])[0]
            if not docs:
                return []

            # Rerank by keyword overlap score
            scored = sorted(
                ((d, _keyword_score(query, d)) for d in docs if d),
                key=lambda t: t[1],
                reverse=True,
            )
            return [doc for doc, _score in scored[:k]]
        except Exception as exc:
            logger.warning("RAG: ChromaDB query failed (%s)", exc)
            return []

    def _retrieve_chromadb_reranked(self, query: str, token_limit: int) -> list[str]:
        """Fetch candidates from ChromaDB, rerank, and accumulate to token budget."""
        try:
            results = self._collection.query(query_texts=[query], n_results=_RERANK_K)
            docs = results.get("documents", [[]])[0]
            if not docs:
                return []

            # Score and sort by keyword overlap
            scored = sorted(
                ((d, _keyword_score(query, d)) for d in docs if d),
                key=lambda t: t[1],
                reverse=True,
            )

            # Accumulate passages up to token budget
            passages: list[str] = []
            total_tokens = 0
            for doc, _score in scored:
                doc_tokens = _estimate_tokens(doc)
                if total_tokens + doc_tokens > token_limit:
                    break
                passages.append(doc)
                total_tokens += doc_tokens

            return passages
        except Exception as exc:
            logger.warning("RAG: ChromaDB reranked query failed (%s)", exc)
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
