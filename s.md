## Типы данных и коллекции

**🟢 1. Уникальные слова.** Дан текст. Посчитай, сколько в нём уникальных слов (без учёта регистра).

- Решение
    
    ```python
    text = "Кот спал кот ел Кот играл"
    words = text.lower().split()
    print(len(set(words)))  # 4
    ```
    

**🟡 2. Частота символов.** Для строки построй словарь `{символ: сколько раз встречается}`, отсортированный по убыванию частоты.
<details>
<summary>Открыт сразу</summary>
    ```python
    from collections import Counter
    s = "abracadabra"
    freq = dict(Counter(s).most_common())
    print(freq)  # {'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1}
    ```
</details>
ewqeqweqwe