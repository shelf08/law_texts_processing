# Руководство по использованию

## Установка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Установка моделей для NLP

Для работы с русским языком необходимо установить модель spaCy:

```bash
python -m spacy download ru_core_news_sm
```

### 3. Настройка GraphDB (опционально)

Если вы используете GraphDB, настройте подключение в файле `.env`:

```
GRAPHDB_HOST=localhost
GRAPHDB_PORT=7200
GRAPHDB_REPOSITORY=law_ontology
GRAPHDB_USERNAME=admin
GRAPHDB_PASSWORD=root
```

## Запуск приложения

### Веб-интерфейс

```bash
python run.py
```

Или напрямую:

```bash
python src/web/app.py
```

Приложение будет доступно по адресу: http://localhost:5000

### Обработка документа через Python

```python
from pathlib import Path
from src.integration.document_processor import DocumentProcessor

processor = DocumentProcessor()
result = processor.process_document(Path("data/raw/example_law.xml"))
print(result)
```

## Использование веб-интерфейса

### 1. Поиск по терминам

- Введите термин или ключевое слово в поле поиска
- Нажмите "Поиск" или Enter
- Результаты отобразятся ниже

### 2. Загрузка документа

- Выберите файл (XML, HTML, PDF, TXT)
- Нажмите "Загрузить и обработать"
- Документ будет проанализирован и добавлен в онтологию

### 3. API endpoints

#### Поиск
```
GET /api/search?q=термин
```

#### Получить статью
```
GET /api/article/<article_id>
```

#### Получить ссылки статьи
```
GET /api/article/<article_id>/references
```

#### Список законов
```
GET /api/laws
```

#### Загрузка документа
```
POST /api/upload
Content-Type: multipart/form-data
file: <file>
```

#### Граф связей
```
GET /api/graph
```

## Работа с онтологией в Protégé

1. Откройте Protégé
2. File → Open → выберите `ontology/legal_ontology.owl`
3. Изучите классы и свойства
4. Добавьте свои данные или импортируйте из приложения

## Экспорт в GraphDB

### Через Protégé

1. В Protégé: File → Export → RDF/XML
2. В GraphDB: Import → RDF file → выберите экспортированный файл

### Через Python

```python
from src.ontology.ontology_manager import OntologyManager
from src.ontology.graphdb_connector import GraphDBConnector

# Загрузка онтологии
manager = OntologyManager()

# Подключение к GraphDB
connector = GraphDBConnector()

# Выполнение SPARQL-запроса
query = """
PREFIX law: <http://law.ontology.ru/#>
SELECT ?law ?title WHERE {
    ?law a law:Law .
    ?law law:hasTitle ?title .
}
"""
results = connector.execute_query(query)
print(results)
```

## Примеры SPARQL-запросов

См. файл `examples/sparql_queries.md` для подробных примеров запросов.

## Структура данных

### Формат XML/HTML документа

Рекомендуемая структура:

```xml
<law>
    <title>Название закона</title>
    <chapter number="1">
        <title>Название главы</title>
        <article number="1">
            Текст статьи...
        </article>
    </chapter>
</law>
```

### Формат TXT документа

```
Название закона

Глава 1. Название главы

Статья 1. Текст статьи...

Статья 2. Текст статьи...
```

## Отладка

Включите логирование:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Логи покажут процесс обработки документов и выполнения запросов.

