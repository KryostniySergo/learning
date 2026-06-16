# Python base

# Подготовка к собеседованию — теоретическая база

> **Как работать с документом:**
1. Сначала изучаешь материалы из блока «Материалы» по теме.
2. Затем отвечаешь на вопросы своими словами — пишешь короткий ответ и **пример кода** в интерпретаторе.
3. На защите домашней работы по теории будут задавать вопросы из этого списка.
4. Вопросы, помеченные ⭐ — спрашивают чаще всего, удели им особое внимание (уточни у наставника полный список «подчёркнутых»).
> 

---

# Часть 1. Python — основы языка

## Материалы для изучения

1. **Как работает Python**
    - https://aws.amazon.com/ru/what-is/python/
    - https://adw0rd.com/2009/08/22/python-howto-work/ (читать до раздела «Средства оптимизации скорости выполнения»)
2. **Различия интерпретатора и компилятора**
    - https://foxminded.ua/ru/kompilyator-i-interpretator/
3. **Типы данных в Python**
    - https://gb.ru/blog/tipy-dannyh-v-python/
    - *P.S. До Python 3.6 словари считались неупорядоченными; с 3.7 — упорядоченные.*
4. **Сложность выполнения операций у list, dict, set**
    - https://proglib.io/p/slozhnost-algoritmov-i-operaciy-na-primere-python-2020-11-03
5. **Как Python работает с памятью**
    - https://tproger.ru/articles/raspredelenie-pamjati-v-python-skolko-i-v-kakih-sluchajah-zanimajut-tipy-dannyh
6. **Особенности словарей и магический метод `__hash__`**
    - https://www.youtube.com/watch?v=Cfx4VCnWeCE (selfedu)
7. **Метаклассы в Python**
    - https://pythonist.ru/metaklassy-v-python/
    - https://sky.pro/media/chto-takoe-metaklassy-v-python/
    - https://sky.pro/media/kak-rabotat-s-metaklassami-v-python/
8. **Анонимные функции (lambda)**
    - https://habr.com/ru/companies/piter/articles/674234/
9. **`__slots__` в Python**
    - https://habr.com/ru/articles/686220/
10. **Декораторы**
    - https://habr.com/ru/companies/otus/articles/727590/
11. **Iterable, Iterator, Generator**
    - Iterable, Iterator — https://youtu.be/TvFQjT7S3kc
    - Generator — https://youtu.be/_k9CoVcNoMU
    - Ещё о генераторах — https://youtu.be/PjZUSSkGLE8?list=PLlWXhlUMyooawilqK4lPXRvxtbYiw34S8
12. **MRO (Method Resolution Order)**
    - https://habr.com/ru/articles/62203/
13. **Type annotation (аннотации типов)**
    - https://tproger.ru/articles/python-typing
14. **ООП и принципы SOLID**
    - ООП — https://www.youtube.com/playlist?list=PLA0M1Bcd0w8zPwP7t-FgwONhZOHt9rz9E
    - SOLID — https://youtu.be/uX8Ot1u3YV0
15. **Магические методы, контекстный менеджер**
    - https://nuancesprog.ru/p/10529/
16. **Конструкция `__name__ == "__main__"`**
    - https://habr.com/ru/articles/702218/
17. **Замыкание (closure)**
    - https://habr.com/ru/articles/781866/
18. **`@classmethod` и `@staticmethod`**
    - https://proproprogs.ru/python_oop/metody-klassa-classmethod-i-staticheskie-metody-staticmethod
19. **LEGB — Local, Enclosing, Global, Built-in**
    - https://habr.com/ru/companies/otus/articles/824554/
20. **GIL — Global Interpreter Lock**
    - https://habr.com/ru/companies/wunderfund/articles/586360/

## Вопросы для подготовки

### Типы данных

- ⭐ Какие типы данных есть?
- На какие категории их можно разделить?

[DataTypeAnswers](/Separate/DataTypes.md)

### Словари, множества и хэшируемые объекты

- ⭐ Как устроен словарь и что такое хэш-таблица?
- ⭐ Что может быть ключами словаря?
- Что такое множество?

[HashTable](/Separate/Hash.md)

### Последовательности, итераторы и генераторы

- ⭐ Что такое итератор и итерируемый объект?
- ⭐ Что такое функция-генератор, объект-генератор и генераторное выражение?
- Чем генератор отличается от итератора?
- Что такое подгенераторы (`yield from`)?
- Что такое контейнерные и плоские последовательности?

[Generators](/Separate/Generators.md)

### Функции

- В чём разница между аргументом и параметром?
- ⭐ Как передаются значения аргументов в функцию или метод?
- ⭐ Что такое замыкание?
- Что такое чистая функция?

[Functions](/Separate/Functions.md)

### Классы и ООП

- ⭐ Что такое ООП?
- ⭐ Какие есть принципы ООП?
- Как происходит доступ к атрибутам и методам классов?
- Что такое `self`?
- ⭐ Что такое магические методы?
- Что такое `super`?
- Что такое дескрипторы?
- Что такое абстрактные классы?
- Когда стоит использовать `__slots__`?
- Когда стоит использовать метаклассы?
- ⭐ Чем содержимое `__dict__` отличается у класса и его экземпляра?

[OPP](/Separate/OOP.md)

### Проектирование

- ⭐ Что такое SOLID?
- На какие категории можно разделить паттерны GoF?

[SOLID](/Separate/SOLID.md)

[GoF](/Separate/GoF.md)

### Декораторы

- ⭐ Что такое декоратор?
- Что может быть декоратором и к чему он может быть применён?
- Зачем нужен `functools.wraps`?

[Decorators](/Separate/Decorators.md)

### Разное

- Что такое Python?
- ⭐ Что такое контекстный менеджер?
- ⭐ Что такое GIL?
- ⭐ Как работает сборщик мусора?
- ⭐ Какая сложность операций в коллекциях (например, добавление элемента в список)?
- ⭐ Что такое LEGB?
- Что такое виртуальное окружение?
- Что такое аннотации типов?
- Для чего нужен `else` в `for`/`while`?
- Для чего нужны `else`/`finally` в `try`/`except`?
- Какие built-in функции знаешь?
- Что такое интернирование?

---

# Часть 2. Web-архитектура

> Прежде чем изучать что-либо, полезно понять: «а для чего это вообще нужно?».
Основные концепции современной web-архитектуры для начинающих веб-разработчиков.
> 

## Материалы для изучения

- Видео — https://www.youtube.com/watch?v=9mZmc6a0tmM
- Оригинал статьи «Web Architecture 101» — https://medium.com/storyblocks-engineering/web-architecture-101-a3224e126947

## Вопросы для подготовки

1. Для каких целей и типов запросов используется кэширование?
2. Каких проблем помогают избежать очереди (брокеры сообщений)?

---

# Часть 3. Архитектура приложения

> Книга «Cosmic Python» (Architecture Patterns with Python).
Для ознакомления: https://www.cosmicpython.com/book/introduction.html
> 
> 
> *При сдаче домашней работы будут задаваться вопросы по теории.*
> 

## Материалы для изучения

1. Domain Modeling — https://www.cosmicpython.com/book/chapter_01_domain_model.html
2. Repository Pattern — https://www.cosmicpython.com/book/chapter_02_repository.html
3. On Coupling and Abstractions — https://www.cosmicpython.com/book/chapter_03_abstractions.html
4. Flask API and Service Layer — https://www.cosmicpython.com/book/chapter_04_service_layer.html
5. TDD in High Gear and Low Gear — https://www.cosmicpython.com/book/chapter_05_high_gear_low_gear.html
6. Unit of Work Pattern — https://www.cosmicpython.com/book/chapter_06_uow.html
7. Aggregates and Consistency Boundaries — https://www.cosmicpython.com/book/chapter_07_aggregate.html

practice_tasks

## Вопросы для подготовки

1. Для чего полезен паттерн «репозиторий»?
2. Чего помогает добиться паттерн «unit of work»?

---

### Памятка по подготовке

1. По каждому вопросу — короткий письменный ответ + пример кода в интерпретаторе.
2. Сформулируй ответ вслух, как будто объясняешь собеседующему.
3. Отметь вопросы, где «плавал», и вернись к ним через день.
4. ⭐-вопросы прогоняй до автоматизма.