# practice_tasks

# Практические задачки по Python

> Маленькие задачки по темам из теории (см. `exam_prep.md`). Сначала реши сам в интерпретаторе,
потом разверни решение и сравни. Не подглядывай раньше времени — так интереснее 🙂
Уровни: 🟢 разминка · 🟡 чуть подумать · 🔴 со звёздочкой.
> 

## Типы данных и коллекции

**🟢 1. Уникальные слова.** Дан текст. Посчитай, сколько в нём уникальных слов (без учёта регистра).

<details>
<summary>Решение</summary>

```Python
text = "Lorem ipsum ipsum dolor sit amet, consectetur adipiscing elit. Integer auctor odio ac nibh vehicula rhoncus. Aliquam tincidunt maximus facilisis. Maecenas."
splited_text = text.lower().split()

result = {}
for word in splited_text:
    if word not in result:
        result.setdefault(word, 1)
    else:
        result[word] += 1

print(len(result))
```

</details>


**🟡 2. Частота символов.** Для строки построй словарь `{символ: сколько раз встречается}`, отсортированный по убыванию частоты.

<details>
<summary>Решение</summary>

```Python
text = "aabbbbbssaa"

result = {}
for symbol in text:
    if symbol not in result:
        result.setdefault(symbol, 0)
    else:
        result[symbol] += 1

print(dict(sorted(result.items(), reverse=True, key=lambda x: x[1])))
```

</details>

**🟡 3. Слияние словарей.** Есть два словаря с числовыми значениями. Сложи значения по общим ключам, остальные перенеси как есть.

<details>
<summary>Решение</summary>

```Python
a = {"x": 1, "y": 2}
b = {"y": 3, "z": 4}

merge = {}
for key in (a.keys() | b.keys()):
    merge[key] = a.get(key, 0) + b.get(key, 0)

print(merge)

merge_v2 = {key: a.get(key, 0) + b.get(key, 0) for key in (a.keys() | b.keys())}

print(merge_v2)
```

</details>

## Хэшируемые объекты

**🟡 4. Что может быть ключом?** Объясни (и проверь в коде), почему список нельзя сделать ключом словаря, а кортеж — можно.

Решение: Потому что список не хешируемый, а кортеж да

## Итераторы и генераторы

**🟢 5. Свой range.** Напиши функцию-генератор `my_range(start, stop, step)`.


<details>
<summary>Решение</summary>

```Python
def my_range(stop: int, step: int = 1, start: int = 0):
    i = start
    while i < stop: 
        i += step
        yield i

for i in my_range(stop=10, step=2, start=3):
    print(i)
```

</details>

**🟡 6. Бесконечный счётчик Фибоначчи.** Генератор, бесконечно выдающий числа Фибоначчи. Возьми первые 10.

<details>
<summary>Решение</summary>

```Python
def fibbonachi():
    a = 0
    b = 1
    c = 0
    while True:
        c = a + b
        yield c
        b = a
        a = c
        
        
fib = fibbonachi()

for i in range(10):
    print(next(fib))
```
</details>

<details>
<summary>Правильное Решение</summary>

```Python
from itertools import islice

def fib():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

print(list(islice(fib(), 10)))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

</details>

**🔴 7. `yield from`.** Напиши генератор `flatten`, который «разворачивает» вложенные списки любой глубины.

<details>
<summary>Правильное Решение</summary>

```Python
def flatten(items):
    for item in items:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item

print(list(flatten([1, [2, [3, 4], 5], [6]])))  # [1, 2, 3, 4, 5, 6]
```

</details>

## Функции и замыкания

**🟢 8. Изменяемый аргумент по умолчанию.** Почему этот код «копит» значения? Как починить?

```python
def add(x, lst=[]):
    lst.append(x)
    return lst
```

Просто передавать list как аргумент

**🟡 9. Замыкание-счётчик.** Сделай функцию `make_counter()`, которая возвращает функцию, увеличивающую и возвращающую счётчик при каждом вызове.

<details>
<summary>Правильное Решение</summary>

```Python
def counter():
    count = 0
    def inc():
        nonlocal count
        count += 1
        return count
    return inc


c = counter()
for _ in range(10):
    print(c())

```

</details>

## Декораторы

**🟡 10. Замер времени.** Напиши декоратор `timer`, печатающий время работы функции. Не забудь `functools.wraps`.

```Python
import functools, time

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__}:{time.perf_counter() - start:.4f}s")
        return result
    return wrapper

@timer
def slow():
    return sum(range(10**6))

slow()
```

**🔴 11. Декоратор с аргументом.** Сделай `repeat(n)`, который выполняет функцию `n` раз и возвращает список результатов.

```Python
import functools

def repeat(n):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return [func(*args, **kwargs) for _ in range(n)]
        return wrapper
    return decorator

@repeat(3)
def greet(name):
    return f"Привет,{name}"

print(greet("Аня"))  # ['Привет, Аня', 'Привет, Аня', 'Привет, Аня']
```

## ООП и магические методы

**🟢 12. Вектор.** Класс `Vector(x, y)` с поддержкой сложения через `+` и красивым выводом `print`.


**🟡 13. Контекстный менеджер.** Напиши класс-менеджер контекста, который печатает «вход»/«выход» и замеряет время блока `with`.



**🟡 14. `__dict__` класса vs экземпляра.** Создай класс с атрибутом класса и атрибутом экземпляра. Покажи, чем отличается `Class.__dict__` от `obj.__dict__`.

## LEGB и области видимости

**🟡 15. global vs nonlocal.** Предскажи вывод, потом проверь:

```python
x = "global"
def outer():
    x = "enclosing"
    def inner():
        nonlocal x
        x = "changed"
    inner()
    print(x)
outer()
print(x)
```
