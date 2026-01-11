"""Модуль интеграции для обработки документов и добавления в онтологию"""
from pathlib import Path
from typing import Dict, List
import logging

from src.ontology.ontology_manager import OntologyManager
from src.text_processing.document_parser import DocumentParser
from src.nlp.text_analyzer import TextAnalyzer
from src.config import CONFIG, PROJECT_ROOT

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Класс для полной обработки документа и добавления в онтологию"""
    
    def __init__(self):
        self.ontology_manager = OntologyManager()
        self.document_parser = DocumentParser()
        self.text_analyzer = TextAnalyzer()
    
    def process_document(self, file_path: Path) -> Dict:
        """Обработать документ и добавить в онтологию"""
        logger.info(f"Обработка документа: {file_path}")
        
        # Парсинг документа
        parsed = self.document_parser.parse(file_path)
        
        # Создание ID для закона
        law_id = file_path.stem.replace(' ', '_').replace('-', '_')
        
        # Добавление закона в онтологию
        law_uri = self.ontology_manager.add_law(
            law_id,
            parsed['title']
        )
        
        # Обработка глав
        chapter_uris = {}
        for chapter in parsed.get('chapters', []):
            chapter_id = f"{law_id}_chapter_{chapter['number']}"
            chapter_uri = self.ontology_manager.add_chapter(
                chapter_id,
                law_uri,
                chapter['number'],
                chapter.get('title', '')
            )
            chapter_uris[chapter['number']] = chapter_uri
        
        # Обработка статей
        article_uris = {}
        for article in parsed.get('articles', []):
            article_id = f"{law_id}_article_{article['number']}"
            
            # Определение главы для статьи (если есть)
            chapter_uri = None
            if parsed.get('chapters'):
                # Простая эвристика: статья принадлежит последней главе
                # В реальной реализации нужно более точное сопоставление
                chapter_uri = list(chapter_uris.values())[-1] if chapter_uris else None
            
            article_uri = self.ontology_manager.add_article(
                article_id,
                chapter_uri,
                article['number'],
                article.get('text', ''),
                law_uri
            )
            article_uris[article['number']] = article_uri
        
        # NLP анализ
        entities = self.text_analyzer.extract_entities(parsed['full_text'])
        references = self.text_analyzer.extract_references(parsed['full_text'])
        key_terms = self.text_analyzer.find_key_terms(parsed['full_text'])
        
        # Добавление терминов в онтологию
        term_uris = {}
        for term_text, freq in key_terms[:20]:  # Топ-20 терминов
            term_id = f"term_{term_text.replace(' ', '_')}"
            term_uri = self.ontology_manager.add_term(term_id, term_text)
            term_uris[term_text] = term_uri
        
        # Связывание терминов со статьями
        for article_num, article_uri in article_uris.items():
            article_text = next((a['text'] for a in parsed.get('articles', []) 
                                if a['number'] == article_num), '')
            
            # Поиск терминов в тексте статьи
            article_lemmas = self.text_analyzer.lemmatize(article_text)
            for term_text, term_uri in term_uris.items():
                if term_text in article_lemmas:
                    self.ontology_manager.link_term_to_article(article_uri, term_uri)
        
        # Обработка ссылок
        for ref in references:
            # Попытка найти ссылаемую статью
            # В реальной реализации нужен более сложный алгоритм
            ref_text = ref['text']
            # Простая эвристика: поиск номера статьи в тексте ссылки
            import re
            article_match = re.search(r'(\d+(?:\.\d+)?)', ref_text)
            if article_match:
                ref_article_num = article_match.group(1)
                if ref_article_num in article_uris:
                    # Ссылка внутри того же закона
                    for article_uri in article_uris.values():
                        self.ontology_manager.add_reference(
                            article_uri,
                            to_article=article_uris.get(ref_article_num)
                        )
        
        # Сохранение онтологии
        self.ontology_manager.save()
        
        logger.info(f"Документ {file_path} успешно обработан и добавлен в онтологию")
        
        return {
            'law_id': law_id,
            'law_uri': str(law_uri),
            'articles_count': len(article_uris),
            'chapters_count': len(chapter_uris),
            'terms_count': len(term_uris),
            'entities': entities,
            'references': references,
            'key_terms': key_terms
        }

