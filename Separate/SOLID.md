
# SOLID в Python

SOLID — это набор из 5 принципов объектно-ориентированного проектирования, которые помогают создавать гибкий, расширяемый и поддерживаемый код.

---

# S — Single Responsibility Principle (SRP)

## Принцип единственной ответственности

Класс должен иметь только одну причину для изменения.

### Плохо

```python
class User:
    def __init__(self, name):
        self.name = name

    def save_to_db(self):
        print(f"Сохраняем {self.name} в БД")
```

Класс отвечает сразу за две вещи:

- хранение данных пользователя;
- сохранение пользователя в БД.

### Хорошо

```python
class User:
    def __init__(self, name):
        self.name = name


class UserRepository:
    def save(self, user: User):
        print(f"Сохраняем {user.name} в БД")
```

Теперь:

- `User` отвечает только за данные;
- `UserRepository` отвечает только за работу с БД.

---

# O — Open/Closed Principle (OCP)

## Принцип открытости/закрытости

Программные сущности должны быть открыты для расширения, но закрыты для изменения.

### Плохо

```python
class Discount:
    def calculate(self, customer_type):
        if customer_type == "regular":
            return 0.05
        elif customer_type == "vip":
            return 0.20
```

Для нового типа клиента придётся изменять существующий код.

### Хорошо

```python
from abc import ABC, abstractmethod


class Discount(ABC):
    @abstractmethod
    def calculate(self):
        pass


class RegularDiscount(Discount):
    def calculate(self):
        return 0.05


class VipDiscount(Discount):
    def calculate(self):
        return 0.20
```

Добавление нового типа:

```python
class PremiumDiscount(Discount):
    def calculate(self):
        return 0.30
```

Существующий код остаётся без изменений.

---

# L — Liskov Substitution Principle (LSP)

## Принцип подстановки Лисков

Объекты дочерних классов должны полностью заменять объекты родительских классов.

### Плохо

```python
class Bird:
    def fly(self):
        pass


class Sparrow(Bird):
    def fly(self):
        print("Лечу")


class Penguin(Bird):
    def fly(self):
        raise Exception("Пингвины не летают")
```

Использование:

```python
def make_bird_fly(bird: Bird):
    bird.fly()
```

Передача `Penguin` приведёт к ошибке.

### Хорошо

```python
class Bird:
    pass


class FlyingBird(Bird):
    def fly(self):
        print("Лечу")


class Sparrow(FlyingBird):
    pass


class Penguin(Bird):
    pass
```

Теперь иерархия отражает реальные возможности объектов.

---

# I — Interface Segregation Principle (ISP)

## Принцип разделения интерфейсов

Клиенты не должны зависеть от методов, которые они не используют.

### Плохо

```python
from abc import ABC, abstractmethod


class Worker(ABC):
    @abstractmethod
    def work(self):
        pass

    @abstractmethod
    def eat(self):
        pass
```

Робот вынужден реализовывать ненужный метод:

```python
class Robot(Worker):
    def work(self):
        print("Работаю")

    def eat(self):
        raise NotImplementedError
```

### Хорошо

```python
from abc import ABC, abstractmethod


class Workable(ABC):
    @abstractmethod
    def work(self):
        pass


class Eatable(ABC):
    @abstractmethod
    def eat(self):
        pass
```

Человек:

```python
class Human(Workable, Eatable):
    def work(self):
        print("Работаю")

    def eat(self):
        print("Ем")
```

Робот:

```python
class Robot(Workable):
    def work(self):
        print("Работаю")
```

---

# D — Dependency Inversion Principle (DIP)

## Принцип инверсии зависимостей

Модули верхнего уровня не должны зависеть от модулей нижнего уровня. Оба должны зависеть от абстракций.

### Плохо

```python
class MySQLDatabase:
    def save(self, data):
        print("Сохраняем в MySQL")


class UserService:
    def __init__(self):
        self.db = MySQLDatabase()
```

Смена базы данных потребует изменения `UserService`.

### Хорошо

```python
from abc import ABC, abstractmethod


class Database(ABC):
    @abstractmethod
    def save(self, data):
        pass


class MySQLDatabase(Database):
    def save(self, data):
        print("Сохраняем в MySQL")


class PostgreSQLDatabase(Database):
    def save(self, data):
        print("Сохраняем в PostgreSQL")
```

Сервис зависит от абстракции:

```python
class UserService:
    def __init__(self, db: Database):
        self.db = db

    def save_user(self, user):
        self.db.save(user)
```

Использование:

```python
db = PostgreSQLDatabase()
service = UserService(db)

service.save_user("Alex")
```

---

# Шпаргалка

| Принцип | Суть |
|----------|------|
| **S** | Один класс — одна ответственность |
| **O** | Расширяй, не изменяя существующий код |
| **L** | Наследники должны корректно заменять родителя |
| **I** | Лучше несколько маленьких интерфейсов |
| **D** | Зависеть от абстракций, а не от реализаций |

---

# SOLID и Python

На практике в Python принципы SOLID чаще всего применяются вместе с:

- `abc.ABC`
- `typing.Protocol`
- Dependency Injection
- Композицией вместо наследования
- Паттернами Repository и Strategy

Следование SOLID позволяет уменьшить связанность компонентов и сделать код более удобным для тестирования и поддержки.
