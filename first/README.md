Чтобы запустить первый тест вам нужно:

1. создать .env в папке first
```
DB_NAME = first
DB_HOST = localhost
DB_PORT = 5432
DB_USER = postgres
DB_PASS = 12345
```
2. Зайти в папку с первым проектом
```
cd first
```
3. Создать контейнер с БД по этой команде:
```
docker compose up -d
```
4. Создать venv:
```
python -m venv .venv
```
5. Создать файл req.txt и скопировать туда пакеты:
```
dotenv==0.9.9
greenlet==3.5.2
psycopg2-binary==2.9.12
python-dotenv==1.2.2
SQLAlchemy==2.0.51
typing_extensions==4.15.0
```
6. Запустить
```
pip install -r req.txt
```
7. Запустить скрипт first_db.py
```
python first_db.py
```