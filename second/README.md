Чтобы запустить второй тест вам нужно:

1. создать .env в папке first
```
DB_NAME = second
DB_HOST = localhost
DB_PORT = 5433
DB_USER = postgres
DB_PASS = 12345
```
- Обратите внимание на порт

2. Зайти в папку с первым проектом
```
cd second
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
aiofiles==25.1.0
aiohappyeyeballs==2.6.2
aiohttp==3.14.1
aiosignal==1.4.0
async==0.6.2
asyncpg==0.31.0
attrs==26.1.0
beautifulsoup4==4.15.0
bs4==0.0.2
certifi==2026.6.17
charset-normalizer==3.4.7
databases==0.9.0
dotenv==0.9.9
frozenlist==1.8.0
greenlet==3.5.2
idna==3.18
multidict==6.7.1
numpy==2.5.0
pandas==3.0.3
propcache==0.5.2
psycopg2-binary==2.9.12
python-dateutil==2.9.0.post0
python-dotenv==1.2.2
requests==2.34.2
six==1.17.0
soupsieve==2.8.4
SQLAlchemy==2.0.51
typing_extensions==4.15.0
urllib3==2.7.0
xlrd==2.0.2
yarl==1.24.2

```
6. Запустить
```
pip install -r req.txt
```
7. Запустить скрипт second.py
```
python second.py
```