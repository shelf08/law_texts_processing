# Инструкция по развертыванию

## Требования

- Python 3.8+
- GraphDB (опционально, для работы с большими объемами данных)

## Быстрый старт

### 1. Клонирование и установка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Установка модели spaCy для русского языка
python -m spacy download ru_core_news_sm

# Скачивание данных для NLTK (если требуется)
python -c "import nltk; nltk.download('punkt')"
```

### 2. Настройка конфигурации

Скопируйте `.env.example` в `.env` и настройте параметры:

```bash
cp .env.example .env
```

Отредактируйте `.env` для настройки GraphDB (если используется).

### 3. Запуск приложения

```bash
python run.py
```

Приложение будет доступно по адресу: http://localhost:5000

## Развертывание GraphDB

### Установка GraphDB

1. Скачайте GraphDB с официального сайта: https://www.ontotext.com/products/graphdb/
2. Установите и запустите GraphDB
3. Создайте новый репозиторий с именем `law_ontology`

### Настройка подключения

В файле `.env` укажите параметры подключения:

```
GRAPHDB_HOST=localhost
GRAPHDB_PORT=7200
GRAPHDB_REPOSITORY=law_ontology
GRAPHDB_USERNAME=admin
GRAPHDB_PASSWORD=root
```

### Импорт онтологии в GraphDB

1. Откройте GraphDB Workbench: http://localhost:7200
2. Выберите репозиторий `law_ontology`
3. Import → RDF file → выберите `ontology/legal_ontology.owl`
4. Нажмите Import

## Производственное развертывание

### Использование Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 src.web.app:app
```

### Использование Docker (пример)

Создайте `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download ru_core_news_sm

COPY . .

EXPOSE 5000

CMD ["python", "run.py"]
```

Сборка и запуск:

```bash
docker build -t law-texts-processing .
docker run -p 5000:5000 law-texts-processing
```

## Мониторинг и логирование

Настройте логирование в `src/web/app.py`:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

## Производительность

### Оптимизация для больших объемов данных

1. Используйте GraphDB вместо файловой онтологии
2. Настройте индексы в GraphDB
3. Используйте кэширование для частых запросов
4. Рассмотрите использование асинхронной обработки (Celery)

### Масштабирование

- Используйте балансировщик нагрузки (nginx)
- Разделите обработку документов на отдельные воркеры
- Используйте очередь задач (Redis + Celery)

