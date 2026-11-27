import math
import re
from pathlib import Path
from typing import Dict, List

from rank_bm25 import BM25Okapi

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class HybridPolicyRetriever:
    def __init__(self):
        self.chunks: List[Dict[str, str]] = []
        self.bm25 = None
        self._load_docs()

    def _load_docs(self):
        if not DOCS_DIR.exists():
            return
        for md_file in sorted(DOCS_DIR.glob("*.md")):
            text = md_file.read_text(encoding="utf-8").strip()
            if not text:
                continue
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for idx, para in enumerate(paragraphs):
                self.chunks.append({
                    "source": md_file.name,
                    "section": f"Section {idx + 1}",
                    "text": para,
                })
        if self.chunks:
            tokenized = [_tokenize(c["text"]) for c in self.chunks]
            self.bm25 = BM25Okapi(tokenized)

    def _cosine_overlap_score(self, q_tokens: List[str], d_tokens: List[str]) -> float:
        if not q_tokens or not d_tokens:
            return 0.0
        q_set, d_set = set(q_tokens), set(d_tokens)
        return len(q_set & d_set) / math.sqrt(len(q_set) * len(d_set))

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        if not self.chunks or not self.bm25:
            return []
        q_tokens = _tokenize(query)
        bm25_scores = self.bm25.get_scores(q_tokens)
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0

        scored = []
        for idx, chunk in enumerate(self.chunks):
            d_tokens = _tokenize(chunk["text"])
            kw_score = bm25_scores[idx] / max_bm25
            sem_score = self._cosine_overlap_score(q_tokens, d_tokens)
            hybrid_score = 0.6 * kw_score + 0.4 * sem_score
            scored.append((hybrid_score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k] if item[0] > 0.05]


policy_retriever = HybridPolicyRetriever()
