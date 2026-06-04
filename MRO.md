# MRO (Method Resolution Order) в Python

## Что такое MRO?

**MRO (Method Resolution Order)** — это порядок, в котором Python ищет атрибуты и методы в иерархии наследования.

Когда выполняется:

```python
obj.method()
```

Python должен определить, в каком классе искать `method`.

Для этого используется MRO.

---

## Простой пример

```python
class A:
    def hello(self):
        print("A")

class B(A):
    pass
```

```python
b = B()
b.hello()
```

Поиск происходит в порядке:

1. B
2. A
3. object

Проверить можно так:

```python
print(B.mro())
```

Результат:

```python
[B, A, object]
```

---

## MRO и множественное наследование

```python
class A:
    def hello(self):
        print("A")

class B:
    def hello(self):
        print("B")

class C(A, B):
    pass
```

```python
c = C()
c.hello()
```

Вывод:

```python
A
```

Потому что:

```python
print(C.mro())
```

даёт:

```python
[C, A, B, object]
```

---

## Как связан super()

Очень важно понимать:

> super() вызывает не родительский класс напрямую, а следующий класс в MRO.

Пример:

```python
class A:
    def hello(self):
        print("A")

class B(A):
    def hello(self):
        print("B")
        super().hello()
```

```python
B().hello()
```

Результат:

```python
B
A
```

---

## Алмазное наследование (Diamond Problem)

```python
class A:
    def hello(self):
        print("A")

class B(A):
    def hello(self):
        print("B")
        super().hello()

class C(A):
    def hello(self):
        print("C")
        super().hello()

class D(B, C):
    def hello(self):
        print("D")
        super().hello()
```

Посмотрим порядок поиска:

```python
print(D.mro())
```

Результат:

```python
[D, B, C, A, object]
```

Теперь вызов:

```python
D().hello()
```

Вывод:

```python
D
B
C
A
```

Обратите внимание:

- A вызывается только один раз.
- super() движется по MRO.
- Python избегает дублирования вызовов.

---

## Как Python вычисляет MRO?

Python использует алгоритм:

**C3 Linearization**

Он гарантирует:

1. Сохранение порядка родителей.
2. Отсутствие повторных вызовов.
3. Предсказуемый порядок поиска методов.

---

## Как посмотреть MRO?

### Способ 1

```python
ClassName.mro()
```

Пример:

```python
D.mro()
```

### Способ 2

```python
ClassName.__mro__
```

Пример:

```python
D.__mro__
```

Результат:

```python
(D, B, C, A, object)
```

---

## Коротко для собеседования

**MRO (Method Resolution Order)** — это порядок поиска атрибутов и методов в иерархии наследования.

- Используется при обращении к методам и атрибутам.
- Используется функцией `super()`.
- Вычисляется алгоритмом **C3 Linearization**.
- Посмотреть можно через `Class.mro()` или `Class.__mro__`.
