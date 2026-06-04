## В чём разница между аргументом и параметром?

Параметр — имя переменной в объявлении функции.

Аргумент — конкретное значение, переданное при вызове функции.

```Python
def greet(name):  # name — параметр
    print(f"Hello, {name}")

greet("Alice")    # "Alice" — аргумент
```

## ⭐ Как передаются значения аргументов в функцию или метод в Python?

В Python аргументы передаются по ссылке на объект (call by object reference / call by sharing). Функция получает ссылку на тот же объект. Изменяемые объекты можно изменить внутри функции, а переназначение параметра не влияет на переменную снаружи.

```Python
def increment(x):
    x += 1

a = 10
increment(a)

print(a)  # 10
```

Что произошло:

1. x и a сначала ссылаются на один объект 10.
2. x += 1 создаёт новый объект 11.
3. Переменная x начинает ссылаться на него.
4. a остаётся ссылаться на старый объект 10.


```Python
def add_item(lst):
    lst.append(4)

numbers = [1, 2, 3]

add_item(numbers)

print(numbers)
```

Вывод:
[1, 2, 3, 4]

Потому что lst и numbers ссылаются на один и тот же список, а метод append() изменяет объект на месте.


## ⭐ Что такое замыкание (Closure)?

Замыкание — это функция, которая:

создана внутри другой функции;
имеет доступ к переменным внешней функции даже после её завершения.

```Python
def make_multiplier(n):
    def multiply(x):
        return x * n
    return multiply

times_3 = make_multiplier(3)

print(times_3(10))
```

Вывод:
```
30
```

![alt text](/Images/Functions.png)

Практическое применение:

- декораторы;
- фабрики функций;
- кэширование;
- инкапсуляция состояния без классов.

Пример счётчика:
```Python
def counter():
    count = 0

    def inc():
        nonlocal count
        count += 1
        return count

    return inc

c = counter()

print(c())  # 1
print(c())  # 2
print(c())  # 3
```

---
nonlocal и local и global

nonlocal — это ключевое слово Python, которое позволяет изменять переменную из ближайшей внешней (не глобальной) области видимости.

Без nonlocal присваивание внутри вложенной функции создаёт новую локальную переменную.

```Python
def outer():
    count = 0

    def inner():
        count += 1  # Ошибка!

    inner()

outer()
```
Вывод ошибка:
```
UnboundLocalError: local variable 'count' referenced before assignment
```

Почему?

Python видит count += 1 и считает, что count — локальная переменная функции inner. Но до присваивания её значение ещё не существует.

Вместе с nonlocal
```Python
def outer():
    count = 0

    def inner():
        nonlocal count
        count += 1
        return count

    inner()
    inner()

    return count

print(outer())
```
Вывод:
```
2
```

![alt text](/Images/nonlocal-first.png)

![alt text](/Images/nonlocal-second.png)

Как запомнить
- local — переменная текущей функции.
- nonlocal — переменная ближайшей внешней функции.
- global — переменная уровня модуля.



## Чистая функция

Для одинаковых входных данных всегда возвращает одинаковый результат.
Не имеет побочных эффектов и не изменяет внешнее состояние.

2. Не имеет побочных эффектов (side effects)

То есть не должна:

- изменять глобальные переменные;
- менять переданные объекты;
- писать в файл;
- отправлять запросы;
- печатать в консоль.