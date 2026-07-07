FROM python:3.12-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём папки для статики и медиа
RUN mkdir -p static media && \
    chown -R 1000:1000 /app

# Переключаемся на непривилегированного пользователя
USER 1000

EXPOSE 8000

# Для разработки
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]