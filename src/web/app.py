"""Веб-приложение Flask для навигации по правовым актам"""
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import logging
from pathlib import Path
import re

from src.config import CONFIG, PROJECT_ROOT
from src.ontology.ontology_manager import OntologyManager, LAW
from src.ontology.graphdb_connector import GraphDBConnector
from src.nlp.text_analyzer import TextAnalyzer
from src.text_processing.document_parser import DocumentParser
from src.web.database import DocumentHistoryDB

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Инициализация компонентов
ontology_manager = OntologyManager()
graphdb_connector = GraphDBConnector() if CONFIG['graphdb'].get('host') else None
text_analyzer = TextAnalyzer()
document_parser = DocumentParser()
document_history_db = DocumentHistoryDB()

# Кеш страниц статей для PDF:
# (doc_id, file_mtime) -> {
#   "map": { "55": 31, ... },
#   "scanned_pages": int,   # сколько страниц уже просмотрено (0..total)
#   "total_pages": int | None,
#   "complete": bool        # досканировали до конца файла
# }
PDF_ARTICLE_PAGE_CACHE: dict[tuple[int, float], dict] = {}

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/search', methods=['GET'])
def search():
    """Поиск по терминам"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'Пустой запрос'}), 400
    
    try:
        def extract_article_title(text: str) -> str | None:
            """Пытаемся извлечь 'название статьи' из начала текста."""
            if not text:
                return None
            # Берём первую непустую строку
            for line in (ln.strip() for ln in text.splitlines()):
                if not line:
                    continue
                # отбрасываем служебные строки
                if 'www.consultant' in line.lower():
                    continue
                if re.search(r'^\(.*ред\..*\)$', line, flags=re.IGNORECASE):
                    continue
                # если строка слишком длинная — это уже тело, не заголовок
                if len(line) > 140:
                    return None
                return line
            return None

        # Поиск в онтологии
        raw_results = ontology_manager.search_articles_by_term(query)
        logger.info(f"Поиск '{query}': найдено {len(raw_results)} результатов")
        if raw_results:
            logger.info(f"Первый результат: {raw_results[0]}")

        def ensure_pdf_pages_for_doc(doc: dict, needed_numbers: set[str]) -> dict[str, int]:
            """
            Инкрементально находим страницы статей в PDF и кешируем.
            Важно: НЕ кешируем "обрезанную" карту навсегда — если позже запросили другие статьи,
            продолжим скан с того места, где остановились.
            """
            try:
                file_path = Path(doc.get('file_path'))
                if not file_path.exists():
                    return {}
                if file_path.suffix.lower() != '.pdf':
                    return {}

                mtime = file_path.stat().st_mtime
                cache_key = (doc['id'], mtime)
                entry = PDF_ARTICLE_PAGE_CACHE.get(cache_key)
                if not entry:
                    entry = {"map": {}, "scanned_pages": 0, "total_pages": None, "complete": False}

                page_map: dict[str, int] = entry.get("map", {})
                if not needed_numbers:
                    return page_map

                # Если всё уже есть — сразу отдаем
                if all(n in page_map for n in needed_numbers):
                    return page_map

                # Если файл уже досканирован до конца — ничего нового не найдём
                if entry.get("complete"):
                    return page_map

                header_re = re.compile(r'^\s*Статья\s+(\d+(?:\.\d+)?)\b', re.IGNORECASE | re.MULTILINE)

                import pdfplumber  # type: ignore
                with pdfplumber.open(file_path) as pdf:
                    total = len(pdf.pages)
                    entry["total_pages"] = total

                    start_idx0 = int(entry.get("scanned_pages") or 0)  # 0-based
                    remaining = {n for n in needed_numbers if n not in page_map}

                    # Продолжаем скан с места остановки
                    for i0 in range(start_idx0, total):
                        text = pdf.pages[i0].extract_text() or ''
                        if text:
                            for m in header_re.finditer(text):
                                num = m.group(1)
                                # первая встреча — страница начала
                                if num not in page_map:
                                    page_map[num] = i0 + 1  # 1-based page number
                                    if num in remaining:
                                        remaining.remove(num)

                        entry["scanned_pages"] = i0 + 1
                        entry["map"] = page_map
                        PDF_ARTICLE_PAGE_CACHE[cache_key] = entry

                        # Если нашли все запрошенные — выходим, но кеш остаётся "неполным"
                        if not remaining:
                            break

                    if entry["scanned_pages"] >= total:
                        entry["complete"] = True
                        entry["map"] = page_map
                        PDF_ARTICLE_PAGE_CACHE[cache_key] = entry

                return page_map
            except Exception:
                return {}

        # Обогащаем результат: документ/файл + название статьи + страница в PDF
        results = []
        # группируем нужные номера по документам (чтобы не сканировать PDF по одному результату)
        needed_by_doc: dict[int, set[str]] = {}
        tmp_rows: list[dict] = []
        for r in raw_results:
            law_uri = r.get('law')
            law_id = None
            if law_uri:
                # http://.../#<law_id>
                law_id = str(law_uri).split('#')[-1]

            doc = document_history_db.get_document_by_law_id(law_id) if law_id else None

            article_text = r.get('article_text') or ''
            article_title = extract_article_title(article_text)

            row = {
                **r,
                'law_id': law_id,
                'law_title': r.get('law_title') or (doc.get('title') if doc else None),
                'document_id': doc.get('id') if doc else None,
                'document_filename': doc.get('filename') if doc else None,
                'document_title': doc.get('title') if doc else None,
                'article_title': article_title,
                # заполнится ниже
                'article_page': r.get('page') or None,
            }
            tmp_rows.append(row)
            if doc and row.get('article_number'):
                needed_by_doc.setdefault(doc['id'], set()).add(str(row['article_number']))

        # подмешиваем страницы (для PDF документов). Здесь сознательно ЖДЕМ,
        # пока страницы для всех результатов будут найдены (если это возможно),
        # чтобы выдача выглядела "полной".
        page_map_by_doc: dict[int, dict[str, int]] = {}
        for doc_id, needed in needed_by_doc.items():
            doc = document_history_db.get_document_by_id(doc_id)
            if doc:
                page_map_by_doc[doc_id] = ensure_pdf_pages_for_doc(doc, needed)

        for row in tmp_rows:
            doc_id = row.get('document_id')
            num = str(row.get('article_number') or '')
            if doc_id and not row.get('article_page') and num:
                row['article_page'] = page_map_by_doc.get(doc_id, {}).get(num)
            results.append(row)

        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/ontology', methods=['GET'])
def debug_ontology():
    """Отладочный endpoint для проверки данных в онтологии"""
    try:
        # Проверяем количество статей
        articles_query = """
        PREFIX law: <http://law.ontology.ru/#>
        SELECT (COUNT(?article) as ?count) WHERE {
            ?article a law:Article .
        }
        """
        articles_result = ontology_manager.query(articles_query)
        
        # Проверяем количество терминов
        terms_query = """
        PREFIX law: <http://law.ontology.ru/#>
        SELECT (COUNT(?term) as ?count) WHERE {
            ?term a law:Term .
        }
        """
        terms_result = ontology_manager.query(terms_query)
        
        # Получаем несколько статей для примера
        sample_articles_query = """
        PREFIX law: <http://law.ontology.ru/#>
        SELECT ?article ?article_number ?article_text WHERE {
            ?article a law:Article .
            ?article law:hasNumber ?article_number .
            OPTIONAL { ?article law:hasText ?article_text . }
        }
        LIMIT 5
        """
        sample_articles = ontology_manager.query(sample_articles_query)
        
        return jsonify({
            'articles_count': articles_result[0].get('count', 'unknown') if articles_result else 0,
            'terms_count': terms_result[0].get('count', 'unknown') if terms_result else 0,
            'sample_articles': sample_articles[:3]
        })
    except Exception as e:
        logger.error(f"Ошибка отладки онтологии: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/article/<article_id>', methods=['GET'])
def get_article(article_id):
    """Получить информацию о статье"""
    try:
        # SPARQL запрос для получения статьи
        query = f"""
        PREFIX law: <{LAW}>
        SELECT ?number ?text ?title WHERE {{
            law:{article_id} law:hasNumber ?number .
            OPTIONAL {{ law:{article_id} law:hasText ?text . }}
            OPTIONAL {{ law:{article_id} law:hasTitle ?title . }}
        }}
        """
        results = ontology_manager.query(query)
        
        if results:
            return jsonify({'article': results[0]})
        else:
            return jsonify({'error': 'Статья не найдена'}), 404
    except Exception as e:
        logger.error(f"Ошибка получения статьи: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/article/<article_id>/references', methods=['GET'])
def get_article_references(article_id):
    """Получить ссылки из статьи"""
    try:
        article_uri = LAW[article_id]
        references = ontology_manager.get_referenced_articles(article_uri)
        
        ref_data = []
        for ref_uri in references:
            query = f"""
            PREFIX law: <{LAW}>
            SELECT ?number ?title WHERE {{
                <{ref_uri}> law:hasNumber ?number .
                OPTIONAL {{ <{ref_uri}> law:hasTitle ?title . }}
            }}
            """
            ref_info = ontology_manager.query(query)
            if ref_info:
                ref_data.append(ref_info[0])
        
        return jsonify({'references': ref_data})
    except Exception as e:
        logger.error(f"Ошибка получения ссылок: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/laws', methods=['GET'])
def get_laws():
    """Получить список всех законов"""
    try:
        query = """
        PREFIX law: <http://law.ontology.ru/#>
        SELECT ?law_id ?title ?date WHERE {
            ?law_id a law:Law .
            ?law_id law:hasTitle ?title .
            OPTIONAL { ?law_id law:hasDate ?date . }
        }
        """
        results = ontology_manager.query(query)
        return jsonify({'laws': results})
    except Exception as e:
        logger.error(f"Ошибка получения законов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Загрузить и обработать документ"""
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Имя файла пустое'}), 400
    
    try:
        # Сохранение файла
        upload_dir = PROJECT_ROOT / CONFIG['data']['input_dir']
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file.filename
        file.save(str(file_path))
        
        # Парсинг документа
        parsed = document_parser.parse(file_path)
        
        # Анализ текста
        entities = text_analyzer.extract_entities(parsed['full_text'])
        references = text_analyzer.extract_references(parsed['full_text'])
        key_terms = text_analyzer.find_key_terms(parsed['full_text'])
        
        # Добавление в онтологию
        law_id = file_path.stem.replace(' ', '_')
        law_uri = ontology_manager.add_law(law_id, parsed['title'])
        
        # Добавление статей
        article_uris = {}
        for article in parsed.get('articles', []):
            article_id = f"{law_id}_article_{article['number']}"
            article_uri = ontology_manager.add_article(
                article_id, 
                None, 
                article['number'],
                article.get('text', ''),
                law_uri,
                page=str(article.get('page')) if article.get('page') else None
            )
            article_uris[article['number']] = article_uri
        
        # Добавление терминов в онтологию и связывание со статьями
        term_uris = {}
        for term_text, freq in key_terms[:20]:  # Топ-20 терминов
            term_id = f"term_{term_text.replace(' ', '_').replace('-', '_')}"
            term_uri = ontology_manager.add_term(term_id, term_text)
            term_uris[term_text] = term_uri
        
        # Связывание терминов со статьями (если термин встречается в тексте статьи)
        linked_count = 0
        for article in parsed.get('articles', []):
            article_uri = article_uris.get(article['number'])
            if article_uri and article.get('text'):
                article_text_lower = article['text'].lower()
                for term_text, term_uri in term_uris.items():
                    term_lower = term_text.lower()
                    # Более точная проверка: ищем слово целиком, а не подстроку
                    if term_lower in article_text_lower:
                        # Проверяем, является ли термин определением (в начале статьи)
                        is_definition = article_text_lower.find(term_lower) < len(article['text']) * 0.1
                        ontology_manager.link_term_to_article(article_uri, term_uri, is_definition)
                        linked_count += 1
        logger.info(f"Связано терминов со статьями: {linked_count}")
        
        # Сохранение онтологии
        ontology_manager.save()
        
        # Сохранение в базу данных истории
        # Подготовка данных для сохранения
        entities_dict = {
            'laws': entities.get('laws', []),
            'articles': entities.get('articles', []),
            'dates': entities.get('dates', []),
            'terms': entities.get('terms', [])
        }
        
        # Вычисляем количество сущностей (сумма всех типов сущностей)
        entities_count = sum(len(v) for v in entities_dict.values() if isinstance(v, list))
        terms_count = len(key_terms) if key_terms else 0
        file_size = file_path.stat().st_size if file_path.exists() else None
        terms_list = [{'term': term[0], 'frequency': term[1]} for term in key_terms]
        
        document_history_db.add_document(
            filename=file.filename,
            law_id=law_id,
            title=parsed.get('title', file.filename),
            file_path=file_path,
            file_size=file_size,
            entities_count=entities_count,
            terms_count=terms_count,
            entities=entities_dict,
            terms=terms_list
        )
        
        return jsonify({
            'message': 'Документ успешно обработан',
            'law_id': law_id,
            'entities': entities,
            'references': references,
            'key_terms': key_terms
        })
    except Exception as e:
        logger.error(f"Ошибка обработки документа: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Получить историю загруженных документов"""
    try:
        documents = document_history_db.get_all_documents()
        return jsonify({'documents': documents})
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/document/<int:doc_id>', methods=['GET'])
def get_document(doc_id):
    """Получить информацию о документе"""
    try:
        doc = document_history_db.get_document_by_id(doc_id)
        if not doc:
            return jsonify({'error': 'Документ не найден'}), 404
        
        # Проверяем существование файла
        file_path = Path(doc['file_path'])
        if not file_path.exists():
            return jsonify({'error': 'Файл документа не найден'}), 404
        
        # Вычисляем количество сущностей из данных
        entities = doc.get('entities', {})
        computed_entities_count = sum(len(v) for v in entities.values() if isinstance(v, list))
        computed_terms_count = len(doc.get('terms', []))
        
        # Используем сохраненные значения из БД, если они есть, иначе вычисляем из данных
        entities_count = doc.get('entities_count')
        if entities_count is None:
            entities_count = computed_entities_count
        
        terms_count = doc.get('terms_count')
        if terms_count is None:
            terms_count = computed_terms_count
        
        return jsonify({
            'id': doc['id'],
            'filename': doc['filename'],
            'title': doc['title'],
            'law_id': doc['law_id'],
            'file_path': str(file_path.relative_to(PROJECT_ROOT)),
            'file_size': doc['file_size'],
            'entities': entities,
            'terms': doc.get('terms', []),
            'entities_count': entities_count,
            'terms_count': terms_count,
            'uploaded_at': doc['uploaded_at']
        })
    except Exception as e:
        logger.error(f"Ошибка получения документа: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/document/<int:doc_id>')
def view_document(doc_id):
    """Страница просмотра документа"""
    return render_template('document.html', doc_id=doc_id)

@app.route('/api/document/<int:doc_id>/file')
def serve_document_file(doc_id):
    """Отдать файл документа для просмотра"""
    try:
        doc = document_history_db.get_document_by_id(doc_id)
        if not doc:
            return jsonify({'error': 'Документ не найден'}), 404
        
        file_path = Path(doc['file_path'])
        if not file_path.exists():
            return jsonify({'error': 'Файл не найден'}), 404
        
        return send_file(str(file_path), as_attachment=False)
    except Exception as e:
        logger.error(f"Ошибка отдачи файла: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/document/<int:doc_id>/article/<article_number>', methods=['GET'])
def get_document_article(doc_id: int, article_number: str):
    """Получить текст статьи из онтологии по документу (law_id) и номеру статьи"""
    try:
        doc = document_history_db.get_document_by_id(doc_id)
        if not doc:
            return jsonify({'error': 'Документ не найден'}), 404

        law_id = doc.get('law_id')
        if not law_id:
            return jsonify({'error': 'У документа нет law_id'}), 400

        article_uri = ontology_manager.get_article_by_number(law_id, article_number)
        if not article_uri:
            return jsonify({'error': 'Статья не найдена'}), 404

        q = f"""
        PREFIX law: <{LAW}>
        SELECT ?number ?text ?title ?page WHERE {{
            <{article_uri}> law:hasNumber ?number .
            OPTIONAL {{ <{article_uri}> law:hasText ?text . }}
            OPTIONAL {{ <{article_uri}> law:hasTitle ?title . }}
            OPTIONAL {{ <{article_uri}> law:hasPage ?page . }}
        }}
        """
        rows = ontology_manager.query(q)
        if not rows:
            return jsonify({'error': 'Статья не найдена'}), 404

        article = rows[0]

        # Если страницы нет в онтологии (старые загрузки) — вычислим по PDF и вернем
        if not article.get('page'):
            try:
                file_path = Path(doc.get('file_path'))
                if file_path.exists() and file_path.suffix.lower() == '.pdf':
                    # используем общий кеш/досканирование, чтобы не гонять PDF с нуля
                    mtime = file_path.stat().st_mtime
                    cache_key = (doc_id, mtime)
                    # чтобы не дублировать код — воспользуемся функцией из /api/search
                    # (внутренний вызов через локальную лямбду тут не получится),
                    # поэтому делаем упрощенно: сначала смотрим кеш, иначе полный поиск по PDF.
                    entry = PDF_ARTICLE_PAGE_CACHE.get(cache_key) or {}
                    page_map = entry.get("map") or {}
                    if str(article_number) in page_map:
                        article['page'] = str(page_map[str(article_number)])
                    else:
                        page = document_parser.find_article_page_in_pdf(file_path, article_number)
                        if page:
                            article['page'] = str(page)
            except Exception:
                pass

        return jsonify({'article': article})
    except Exception as e:
        logger.error(f"Ошибка получения статьи документа: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/document/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Удалить документ из истории"""
    try:
        doc = document_history_db.get_document_by_id(doc_id)
        if not doc:
            return jsonify({'error': 'Документ не найден'}), 404
        
        # Удаляем из БД
        deleted = document_history_db.delete_document(doc_id)
        
        if deleted:
            # Опционально: можно также удалить файл
            # file_path = Path(doc['file_path'])
            # if file_path.exists():
            #     file_path.unlink()
            
            return jsonify({'message': 'Документ успешно удален'})
        else:
            return jsonify({'error': 'Не удалось удалить документ'}), 500
    except Exception as e:
        logger.error(f"Ошибка удаления документа: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(
        host=CONFIG['web']['host'],
        port=CONFIG['web']['port'],
        debug=CONFIG['web']['debug']
    )

