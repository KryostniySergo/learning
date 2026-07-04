# Теория по Django (+ DRF)

Конспект по программе обучения. **Перед стартом прочитать:** Чистая архитектура в Django (vivid_money) — задаёт общий взгляд на структуру проекта.

**Навигация по темам:**
1. Введение в Django
2. Шаблонизация и стилизация
3. Работа с базой данных (ORM)
4. Динамические страницы
5. Django REST Framework (DRF)
6. Продвинутые темы

---

## 1. Введение в Django

> 📚 Материалы: Что такое Django (Habr) · Подготовка venv (metanit) · Добавление Django-приложения (itproger)
> 

### Что такое Django

Django — высокоуровневый веб-фреймворк на Python, построенный по принципу **«batteries included»** (всё в комплекте: ORM, админка, аутентификация, формы, маршрутизация).

- **Архитектурный паттерн — MTV** (Model–Template–View), вариация MVC:
    - **Model** — данные и бизнес-логика работы с БД (ORM).
    - **Template** — представление (HTML с шаблонным языком).
    - **View** — логика обработки запроса, связывает модель и шаблон.
    - Роль «контроллера» играет сам фреймворк (роутер URL).
- **DRY** (Don’t Repeat Yourself) — ключевая философия Django.

### Структура проекта

```
myproject/
├── manage.py            # CLI для управления проектом
├── myproject/           # пакет проекта (конфигурация)
│   ├── settings.py      # настройки
│   ├── urls.py          # корневая маршрутизация
│   ├── wsgi.py / asgi.py# точки входа для серверов
└── myapp/               # приложение
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── apps.py
    └── migrations/
```

- **Проект** ≠ **приложение**. Проект — это сайт целиком; приложение — переиспользуемый модуль внутри (блог, магазин, API).

### Виртуальное окружение (venv)

Изоляция зависимостей проекта от системного Python.

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows
pip install django
pip freeze > requirements.txt
```

### Создание проекта и приложения

```bash
django-admin startproject myproject .
python manage.py startapp myapp
```

Приложение нужно зарегистрировать в `INSTALLED_APPS` в `settings.py`.

---

## 2. Шаблонизация и стилизация

> 📚 Материалы: Шаблонизатор и HTML-шаблоны (itproger) · Статические файлы и Bootstrap (itproger) · Передача данных в шаблоны (itproger)
> 

### Шаблонизатор

Django использует собственный язык шаблонов (DTL), синтаксически близкий к Jinja2.

- **Переменные:** `{{ variable }}`
- **Теги (логика):** `{% if %}`, `{% for %}`, `{% block %}`, `{% extends %}`, `{% include %}`
- **Фильтры:** `{{ name|upper }}`, `{{ date|date:"d.m.Y" }}`, `{{ text|truncatewords:20 }}`
- **Наследование шаблонов:** базовый `base.html` с `{% block content %}{% endblock %}`, дочерние шаблоны через `{% extends "base.html" %}`.

### Статические файлы

- Настройки: `STATIC_URL`, `STATICFILES_DIRS`, `STATIC_ROOT`.
- В шаблоне: `{% load static %}` → `<link href="{% static 'css/style.css' %}">`.
- Bootstrap подключается как статика или через CDN.

### Передача данных в шаблон

View передаёт `context` (словарь) в `render`:

```python
def index(request):
    return render(request, "index.html", {"posts": Post.objects.all()})
```

---

## 3. Работа с базой данных (ORM)

> 📚 Материалы: Создание модели (itproger) · Вывод записей из БД (itproger) · Форма для добавления записей (itproger)
> 

### Модель

Класс-наследник `models.Model`. Каждая модель = таблица, поле = колонка.

```python
class Post(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

**Основные типы полей:** `CharField`, `TextField`, `IntegerField`, `BooleanField`, `DateTimeField`, `ForeignKey`, `ManyToManyField`, `OneToOneField`, `DecimalField`, `EmailField`.

**Связи:**
- `ForeignKey` — один-ко-многим (у собаки одна порода, у породы много собак). Параметр `on_delete` обязателен (`CASCADE`, `PROTECT`, `SET_NULL`).
- `ManyToManyField` — многие-ко-многим.
- `OneToOneField` — один-к-одному.

### Миграции

Перенос изменений моделей в схему БД:

```bash
python manage.py makemigrations   # создать файл миграции
python manage.py migrate          # применить к БД
```

### Запросы (QuerySet API)

```python
Post.objects.all()
Post.objects.filter(title__icontains="django")
Post.objects.get(id=1)
Post.objects.exclude(...)
Post.objects.order_by("-created")
Post.objects.create(title="...", body="...")
```

- **Lookups:** `__gt`, `__lt`, `__gte`, `__lte`, `__in`, `__icontains`, `__startswith`, `__isnull`.
- QuerySet **ленивый** — запрос к БД выполняется только при обращении к данным (итерация, `list()`, срез, `len`).

### Формы

- `forms.Form` — обычная форма.
- `forms.ModelForm` — форма на основе модели (автоматически генерирует поля).

```python
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "body"]
```

---

## 4. Динамические страницы

> 📚 Материалы: Динамически изменяемые страницы (itproger) · Редактирование и удаление записей (itproger) · Создание пробного приложения (itproger)
> 
- **URL-параметры:** `path("post/<int:pk>/", views.detail)` → захват `pk` в URL.
- **CRUD на функциях/классах:**
    - Создание — `POST` + форма.
    - Редактирование — получить объект, заполнить форму `instance=obj`, сохранить.
    - Удаление — `obj.delete()`.
- **CBV (Class-Based Views):** `ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView` — готовые классы, сокращающие шаблонный код.

---

## 5. Django REST Framework (DRF)

> 📚 Материалы: Официальная документация / QuickStart · Сериализаторы и view-функции (Я.Практикум) · Создание API на DRF (Habr)
> 

Библиотека для построения REST API поверх Django.

### Сериализаторы

Преобразуют сложные типы (модели, QuerySet) ↔︎ JSON и валидируют входные данные.

```python
class DogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dog
        fields = "__all__"
```

- `Serializer` — ручное описание полей.
- `ModelSerializer` — автогенерация полей из модели.
- `SerializerMethodField` — вычисляемое поле (`get_<field>`).

### Views

- `APIView` — базовый класс (ручная обработка методов).
- **Generic views** — `ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`.
- **ViewSet / ModelViewSet** — объединяет CRUD в один класс; работает с роутерами.

```python
class DogViewSet(viewsets.ModelViewSet):
    queryset = Dog.objects.all()
    serializer_class = DogSerializer
```

### Роутеры

Автоматически генерируют URL для ViewSet:

```python
router = DefaultRouter()
router.register("dogs", DogViewSet)
urlpatterns = router.urls
```

### Прочее в DRF

- **Аутентификация / Permissions** — `IsAuthenticated`, `IsAdminUser`, кастомные.
- **Пагинация, фильтрация, throttling.**
- **Status codes** — `rest_framework.status`.

---

## 6. Продвинутые темы

> 📚 Материалы: Сигналы (док-я) · Оптимизация запросов / `select_related` и `prefetch_related` (док-я) · Generic Foreign Key (док-я) · Celery + Django (док-я)
> 

### Сигналы (Signals)

Механизм «издатель–подписчик» для реакции на события ORM/фреймворка.
- Встроенные: `pre_save`, `post_save`, `pre_delete`, `post_delete`, `m2m_changed`.
- Подключение через декоратор `@receiver`.
- ⚠️ Минусы: неявность, усложняют отладку. Для сложной логики часто предпочитают явные сервисы.

### Продвинутый ORM

- **`select_related`** — JOIN для `ForeignKey`/`OneToOne` (один запрос). Решает N+1 для «прямых» связей.
- **`prefetch_related`** — отдельный запрос + объединение в Python для `ManyToMany` и обратных FK.
- **`annotate`** — добавляет вычисляемое поле к каждому объекту (`Count`, `Avg`, `Sum`).
- **`aggregate`** — агрегат по всему QuerySet (одно значение).
- **`F()`** — ссылка на поле БД (атомарные операции без гонок: `F("views") + 1`).
- **`Q()`** — сложные условия с `AND`/`OR`/`NOT`.
- **`Subquery` / `OuterRef`** — подзапросы, ссылающиеся на внешний запрос.

#### Проблема N+1

Когда в цикле по объектам для каждого делается отдельный запрос к связанной таблице. Решается `select_related`/`prefetch_related`.

### Generic Foreign Key

Связь с **любой** моделью через `ContentType`:

```python
content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
object_id = models.PositiveIntegerField()
content_object = GenericForeignKey("content_type", "object_id")
```

Применение: комментарии/лайки/теги для разных моделей.

### Фоновые задачи (Celery + Redis)

- **Celery** — очередь задач для асинхронной/отложенной работы (рассылки, обработка файлов, отчёты).
- **Redis / RabbitMQ** — брокер сообщений между Django и воркерами Celery.
- **Celery Beat** — периодические задачи по расписанию.