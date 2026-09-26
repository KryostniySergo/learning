import threading
from collections import OrderedDict
from typing import Any


class Embedder:
    """Превращает тексты в векторы для поиска.

    Документы и запросы кодируются разными методами, потому что модели семейства e5
    обучены с префиксами: "passage: " для документов и "query: " для запросов.
    Для других моделей префиксы не добавляются — им они только мешают.

    Векторы нормализованы до длины 1, поэтому скалярное произведение двух векторов
    равно их косинусной близости.
    """

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        cache_size: int = 1024,
        model: Any | None = None,
    ) -> None:
        """Загружает модель.

        Args:
            model_name: имя модели на Hugging Face, например "intfloat/multilingual-e5-small".
            device: "cpu" или "cuda".
            cache_size: сколько последних запросов держать в кеше.
            model: готовый объект модели вместо загрузки по имени. Нужен для тестов:
                туда можно передать фейк с методом encode и не качать настоящую модель.
        """
        if model is None:
            # импорт внутри: библиотека тянет torch и грузится несколько секунд,
            # а тестам с фейковой моделью она вообще не нужна
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(model_name, device=device)
        self.model_name = model_name
        self._model = model
        self._is_e5 = "e5" in model_name.lower()
        self._cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self._cache_size = cache_size
        self._lock = threading.Lock()  # кеш трогают из нескольких потоков (run_in_threadpool)

    @property
    def dim(self) -> int:
        """Размерность векторов модели (384 у e5-small, 768 у e5-base).

        В новых версиях sentence-transformers метод называется get_embedding_dimension,
        старое имя get_sentence_embedding_dimension устарело (FutureWarning).
        Берём новое, а старое оставляем для совместимости со старыми версиями.
        """
        getter = getattr(self._model, "get_embedding_dimension", None)
        if getter is None:
            getter = self._model.get_sentence_embedding_dimension
        return getter()

    def _encode(self, texts: list[str], batch_size: int) -> list[list[float]]:
        """Кодирует уже подготовленные тексты (с префиксами) в нормализованные векторы."""
        vectors = self._model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Кодирует фрагменты для индексации. Для e5 добавляет префикс "passage: "."""
        prepared = [f"passage: {t}" for t in texts] if self._is_e5 else list(texts)
        return self._encode(prepared, batch_size)

    def embed_query(self, text: str) -> list[float]:
        """Кодирует поисковый запрос. Для e5 добавляет префикс "query: ".

        Результат кешируется: одинаковые запросы (с точностью до лишних пробелов)
        не гоняются через модель повторно. Регистр не меняем — модель к нему чувствительна.
        """
        key = " ".join(text.split())
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)  # свежий запрос — в конец очереди
                return list(self._cache[key])

        prepared = f"query: {key}" if self._is_e5 else key
        vector = self._encode([prepared], batch_size=1)[0]

        with self._lock:
            self._cache[key] = tuple(vector)  # кортеж: снаружи кеш не испортить
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)  # выкидываем самый старый
        return vector
