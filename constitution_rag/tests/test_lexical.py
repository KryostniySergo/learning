from app.search.lexical import BM25Index, tokenize


def test_tokenize_stems_word_forms():
    """Разные падежи одного слова дают одинаковый токен."""
    assert tokenize("Президента") == tokenize("президентом") == tokenize("Президент")


def test_tokenize_keeps_compound_numbers_and_yo():
    """Номер "67.1" — один токен; "ё" приводится к "е"."""
    assert "67.1" in tokenize("Статья 67.1", stem=False)
    assert tokenize("её", stem=False) == ["ее"]


def test_bm25_finds_by_word_form():
    """Со стеммингом запрос в одной форме находит текст с другой формой слова."""
    index = BM25Index(
        ["a", "b", "c"],
        ["Президент избирается сроком на шесть лет", "Жилище неприкосновенно", "Суды осуществляют правосудие"],
    )
    assert index.search("срок полномочий президента", k=3)[0] == "a"


def test_bm25_skips_documents_without_common_words():
    """Документы без общих слов с запросом не возвращаются вовсе."""
    index = BM25Index(["a", "b", "c"], ["Жилище неприкосновенно", "Суды независимы", "Труд свободен"])
    assert index.search("жилище", k=5) == ["a"]
