"""Семантический поиск по статьям правовых актов"""
import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class SemanticSearch:
    """Семантический поиск на основе sentence-transformers (multilingual)"""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Загружена модель семантического поиска: {self.model_name}")
        except ImportError:
            logger.warning(
                "sentence-transformers не установлен. "
                "Запустите: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(f"Ошибка загрузки модели '{self.model_name}': {e}")

    @property
    def available(self) -> bool:
        return self.model is not None

    def embed(self, texts: List[str]) -> np.ndarray:
        if not self.available:
            raise RuntimeError("Модель семантического поиска не загружена")
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,
        )

    def search(
        self,
        query: str,
        indexed_articles: List[Dict],
        top_k: int = 20,
        min_score: float = 0.15,
    ) -> List[Dict]:
        """
        indexed_articles: list of dicts с ключами:
            law_id, article_number, article_text, embedding (np.ndarray)
        Возвращает top_k статей, отсортированных по косинусному сходству,
        с добавленным полем semantic_score (0..1).
        """
        if not self.available or not indexed_articles:
            return []

        query_emb = self.embed([query])[0]
        embeddings = np.stack([a["embedding"] for a in indexed_articles])

        q_norm = query_emb / (np.linalg.norm(query_emb) + 1e-9)
        e_norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9
        scores = (embeddings / e_norms) @ q_norm

        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < min_score:
                break
            row = {k: v for k, v in indexed_articles[idx].items() if k != "embedding"}
            row["semantic_score"] = round(score, 4)
            results.append(row)

        return results
