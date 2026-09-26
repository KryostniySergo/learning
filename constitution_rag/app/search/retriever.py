from app.search.embedder import Embedder
from app.search.store import ChromaStore, Hit


class Retriever:
    """Единая точка поиска для API и скриптов оценки: вопрос -> список найденных фрагментов."""

    def __init__(self, embedder: Embedder, store: ChromaStore, settings) -> None:
        """Запоминает зависимости.

        Args:
            embedder: модель для кодирования запроса.
            store: векторное хранилище.
            settings: настройки (понадобятся на этапе 8: candidate_k, min_score, use_hybrid).
        """
        self._embedder = embedder
        self._store = store
        self._settings = settings

    def retrieve(self, query: str, k: int) -> list[Hit]:
        """Возвращает до k фрагментов, самые близкие к запросу первыми.

        Синхронный и CPU-тяжёлый (внутри работает модель), поэтому из async-кода
        его нужно вызывать через run_in_threadpool.
        """
        vector = self._embedder.embed_query(query)
        return self._store.search(vector, k)
