"""Модуль для работы с онтологией правовых актов"""
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL
from rdflib.query import ResultRow
from pathlib import Path
from typing import List, Dict, Optional
import logging
import re

from src.config import CONFIG, PROJECT_ROOT

logger = logging.getLogger(__name__)

# Пространство имен онтологии
LAW = Namespace(CONFIG['ontology']['namespace'])

_XML_ALLOWED_CONTROL_BYTES = {9, 10, 13}  # \t, \n, \r

def _sanitize_rdfxml_file(source_path: Path, target_path: Path) -> None:
    """
    Пытаемся "починить" RDF/XML файл, если он содержит недопустимые байты (NUL и др.)
    или неэкранированные амперсанды в текстовых полях.

    Это не идеальный "ремонт онтологии", а практичный способ не падать при старте приложения.
    """
    raw = source_path.read_bytes()

    # 1) Удаляем недопустимые для XML 1.0 управляющие символы (0x00..0x1F кроме \t,\n,\r)
    cleaned = bytes(b for b in raw if b >= 32 or b in _XML_ALLOWED_CONTROL_BYTES)

    # 2) Декодируем с заменой битых последовательностей, чтобы не падать на UTF-8
    text = cleaned.decode("utf-8", errors="replace")

    # 3) Экранируем '&', если он не начинает валидную XML-entity
    #    (частая причина "not well-formed (invalid token)")
    text = re.sub(
        r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9A-Fa-f]+;)',
        "&amp;",
        text,
    )

    target_path.write_text(text, encoding="utf-8")

class OntologyManager:
    """Класс для управления онтологией правовых актов"""
    
    def __init__(self):
        self.graph = Graph()
        self.graph.bind("law", LAW)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        
        # Загрузка онтологии
        ontology_path = PROJECT_ROOT / CONFIG['ontology']['file']
        if ontology_path.exists():
            try:
                self.graph.parse(str(ontology_path), format="xml")
                logger.info(f"Онтология загружена из {ontology_path}")
            except Exception as e:
                # В онтологии (особенно при автоматическом наполнении из PDF) могут появляться
                # недопустимые XML-байты (NUL) или неэкранированные '&'. В таком случае
                # создаём "санитизированную" копию и пробуем загрузить её.
                sanitized_path = ontology_path.parent / f"{ontology_path.stem}.sanitized{ontology_path.suffix}"
                logger.warning(
                    "Не удалось распарсить RDF/XML онтологию (%s). "
                    "Пробуем создать санитизированную копию: %s",
                    e,
                    sanitized_path,
                )
                _sanitize_rdfxml_file(ontology_path, sanitized_path)
                self.graph.parse(str(sanitized_path), format="xml")
                logger.info(f"Онтология загружена из санитизированного файла {sanitized_path}")
    
    def add_law(self, law_id: str, title: str, date: str = None) -> URIRef:
        """Добавить закон в онтологию"""
        law_uri = LAW[law_id]
        self.graph.add((law_uri, RDF.type, LAW.Law))
        self.graph.add((law_uri, LAW.hasTitle, Literal(title, lang="ru")))
        if date:
            self.graph.add((law_uri, LAW.hasDate, Literal(date, datatype="http://www.w3.org/2001/XMLSchema#date")))
        return law_uri
    
    def add_chapter(self, chapter_id: str, law_uri: URIRef, number: str, title: str = None) -> URIRef:
        """Добавить главу в онтологию"""
        chapter_uri = LAW[chapter_id]
        self.graph.add((chapter_uri, RDF.type, LAW.Chapter))
        self.graph.add((chapter_uri, LAW.hasNumber, Literal(number)))
        if title:
            self.graph.add((chapter_uri, LAW.hasTitle, Literal(title, lang="ru")))
        self.graph.add((law_uri, LAW.containsChapter, chapter_uri))
        return chapter_uri
    
    def add_article(self, article_id: str, chapter_uri: URIRef, number: str,
                   text: str = None, law_uri: URIRef = None, page: str = None) -> URIRef:
        """Добавить статью в онтологию"""
        article_uri = LAW[article_id]
        self.graph.add((article_uri, RDF.type, LAW.Article))
        self.graph.add((article_uri, LAW.hasNumber, Literal(number)))
        if text:
            self.graph.add((article_uri, LAW.hasText, Literal(text, lang="ru")))
        if page:
            # не требует явного описания свойства в OWL — достаточно триплета
            self.graph.add((article_uri, LAW.hasPage, Literal(str(page))))
        if chapter_uri:
            self.graph.add((chapter_uri, LAW.containsArticle, article_uri))
        if law_uri:
            self.graph.add((article_uri, LAW.belongsToLaw, law_uri))
        return article_uri
    
    def add_term(self, term_id: str, term_text: str) -> URIRef:
        """Добавить термин в онтологию"""
        term_uri = LAW[term_id]
        self.graph.add((term_uri, RDF.type, LAW.Term))
        self.graph.add((term_uri, LAW.hasTitle, Literal(term_text, lang="ru")))
        return term_uri
    
    def add_reference(self, from_article: URIRef, to_article: URIRef = None, 
                     to_law: URIRef = None):
        """Добавить ссылку между статьями или на закон"""
        if to_article:
            self.graph.add((from_article, LAW.references, to_article))
        if to_law:
            self.graph.add((from_article, LAW.referencesLaw, to_law))
    
    def add_synonym(self, term1: URIRef, term2: URIRef):
        """Добавить синонимическую связь между терминами"""
        self.graph.add((term1, LAW.hasSynonym, term2))
    
    def link_term_to_article(self, article_uri: URIRef, term_uri: URIRef, is_definition: bool = False):
        """Связать термин со статьей"""
        if is_definition:
            self.graph.add((article_uri, LAW.definesTerm, term_uri))
        else:
            self.graph.add((article_uri, LAW.usesTerm, term_uri))
    
    def save(self, output_path: Optional[Path] = None):
        """Сохранить онтологию в файл"""
        if output_path is None:
            output_path = PROJECT_ROOT / CONFIG['ontology']['file']
        self.graph.serialize(destination=str(output_path), format="xml")
        logger.info(f"Онтология сохранена в {output_path}")
    
    def query(self, sparql_query: str) -> List[Dict]:
        """Выполнить SPARQL-запрос"""
        results = []
        try:
            query_result = self.graph.query(sparql_query)
            # В rdflib Row/ResultRow — это маппинг Variable -> value.
            # Важно: проверка `var_name in row` здесь НЕ работает как проверка ключей,
            # из-за чего все значения превращались в None.
            variables = list(query_result.vars)  # rdflib.term.Variable

            for row in query_result:
                # На практике rdflib (в т.ч. 6/7) возвращает здесь ключи-строки: {'var': value}
                # поэтому читаем по строковому имени переменной.
                row_bindings = row.asdict()  # {'x': value, ...}
                result_dict: Dict[str, Optional[str]] = {}

                for var in variables:
                    var_name = str(var).lstrip('?')
                    value = row_bindings.get(var_name)

                    if value is None:
                        result_dict[var_name] = None
                        continue

                    # Преобразуем значение в строку для JSON-ответов
                    result_dict[var_name] = str(value)

                results.append(result_dict)
        except Exception as e:
            logger.error(f"Ошибка выполнения SPARQL запроса: {e}", exc_info=True)
            logger.error(f"Запрос: {sparql_query}")
            raise
        return results
    
    def get_article_by_number(self, law_id: str, article_number: str) -> Optional[URIRef]:
        """Найти статью по номеру"""
        query = f"""
        PREFIX law: <{LAW}>
        SELECT ?article WHERE {{
            ?article a law:Article ;
                     law:hasNumber "{article_number}" ;
                     law:belongsToLaw law:{law_id} .
        }}
        """
        results = self.query(query)
        if results:
            return results[0].get('article')
        return None
    
    def get_referenced_articles(self, article_uri: URIRef) -> List[URIRef]:
        """Получить все статьи, на которые ссылается данная статья"""
        query = f"""
        PREFIX law: <{LAW}>
        SELECT ?ref_article WHERE {{
            <{article_uri}> law:references ?ref_article .
        }}
        """
        results = self.query(query)
        return [row.get('ref_article') for row in results if row.get('ref_article')]
    
    def search_articles_by_term(self, term_text: str) -> List[Dict]:
        """Найти статьи, содержащие или определяющие термин"""
        # Экранируем специальные символы для SPARQL-строки
        # (сначала backslash, потом кавычки)
        term_text_escaped = term_text.replace('\\', '\\\\').replace('"', '\\"')
        
        # Сначала ищем по терминам в онтологии
        query1 = f"""
        PREFIX law: <{LAW}>
        SELECT ?article ?article_number ?article_text ?law ?law_title WHERE {{
            ?term a law:Term ;
                  law:hasTitle ?term_title .
            FILTER(CONTAINS(LCASE(?term_title), LCASE("{term_text_escaped}")))
            {{
                ?article law:definesTerm ?term .
            }} UNION {{
                ?article law:usesTerm ?term .
            }}
            ?article law:hasNumber ?article_number .
            OPTIONAL {{ ?article law:hasText ?article_text . }}
            OPTIONAL {{ ?article law:belongsToLaw ?law . }}
            OPTIONAL {{ ?law law:hasTitle ?law_title . }}
        }}
        """
        results = self.query(query1)
        logger.info(f"Поиск по терминам в онтологии для '{term_text}': найдено {len(results)} результатов")
        
        # Если результатов нет, ищем по тексту статей напрямую
        if not results:
            query2 = f"""
            PREFIX law: <{LAW}>
            SELECT ?article ?article_number ?article_text ?law ?law_title WHERE {{
                ?article a law:Article ;
                         law:hasNumber ?article_number ;
                         law:hasText ?article_text .
                FILTER(CONTAINS(LCASE(?article_text), LCASE("{term_text_escaped}")))
                OPTIONAL {{ ?article law:belongsToLaw ?law . }}
                OPTIONAL {{ ?law law:hasTitle ?law_title . }}
            }}
            LIMIT 50
            """
            results = self.query(query2)
            logger.info(f"Поиск по тексту статей для '{term_text}': найдено {len(results)} результатов")

            # Если точное CONTAINS не сработало (часто из-за переносов строк/множественных пробелов),
            # пробуем более устойчивый REGEX: заменяем пробелы на \\s+.
            if not results and any(ch.isspace() for ch in term_text):
                raw = term_text.strip().lower()
                regex = re.escape(raw).replace(r"\ ", r"\\s+")
                query3 = f"""
                PREFIX law: <{LAW}>
                SELECT ?article ?article_number ?article_text ?law ?law_title WHERE {{
                    ?article a law:Article ;
                             law:hasNumber ?article_number ;
                             law:hasText ?article_text .
                    FILTER(REGEX(LCASE(STR(?article_text)), "{regex}"))
                    OPTIONAL {{ ?article law:belongsToLaw ?law . }}
                    OPTIONAL {{ ?law law:hasTitle ?law_title . }}
                }}
                LIMIT 50
                """
                results = self.query(query3)
                logger.info(f"Поиск по тексту (REGEX) для '{term_text}': найдено {len(results)} результатов")
        
        # Нормализуем ключи результатов (убираем префикс ? если есть)
        normalized_results = []
        for result in results:
            normalized = {}
            for key, value in result.items():
                # Убираем префикс ? из ключа
                clean_key = key.lstrip('?')
                normalized[clean_key] = value
            normalized_results.append(normalized)
        
        logger.info(f"Итого результатов для '{term_text}': {len(normalized_results)}")
        return normalized_results

