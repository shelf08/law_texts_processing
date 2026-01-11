"""Модуль NLP для анализа и аннотации правовых актов"""
import re
import logging
from typing import List, Dict, Set, Tuple, Iterable
from collections import Counter

try:
    import spacy
    from spacy.lang.ru import Russian
except ImportError:
    spacy = None

try:
    import pymorphy3
except ImportError:
    try:
        import pymorphy2
        pymorphy3 = None
    except ImportError:
        pymorphy2 = None
        pymorphy3 = None

from src.config import CONFIG

logger = logging.getLogger(__name__)

class TextAnalyzer:
    """Класс для NLP анализа правовых текстов"""
    
    def __init__(self):
        self.config = CONFIG['nlp']
        self.nlp = None
        self.morph = None
        self.spacy_safe_max_chars = int(self.config.get('spacy_safe_max_chars', 400_000))
        self.key_terms_max_chars = int(self.config.get('key_terms_max_chars', 1_500_000))
        
        # Инициализация spaCy
        if spacy:
            try:
                model_name = self.config.get('spacy_model', 'ru_core_news_sm')
                # Нам не нужен NER/парсер для текущих задач → отключаем, чтобы снизить память.
                self.nlp = spacy.load(model_name, disable=["ner", "parser"])
                # Поднимаем жесткий лимит длины текста (иначе E088 на больших документах)
                self.nlp.max_length = int(self.config.get('spacy_max_length', 5_000_000))
                logger.info(f"Загружена модель spaCy: {model_name}")
            except OSError:
                logger.warning(f"Модель {model_name} не найдена. Используется базовый русский язык.")
                self.nlp = Russian()
        
        # Инициализация pymorphy3 (предпочтительно) или pymorphy2
        if pymorphy3:
            try:
                self.morph = pymorphy3.MorphAnalyzer()
                logger.info("Инициализирован pymorphy3")
            except Exception as e:
                logger.warning(f"Ошибка инициализации pymorphy3: {e}")
                self.morph = None
        elif pymorphy2:
            try:
                self.morph = pymorphy2.MorphAnalyzer()
                logger.info("Инициализирован pymorphy2")
            except Exception as e:
                logger.warning(f"Ошибка инициализации pymorphy2: {e}")
                self.morph = None
    
    def _iter_tokens_regex(self, text: str) -> Iterable[str]:
        """Итератор токенов без spaCy (быстро и безопасно для больших текстов)."""
        # \w включает цифры/подчеркивания; для правовых текстов этого достаточно
        for m in re.finditer(r'\b\w+\b', text.lower()):
            yield m.group(0)

    def tokenize(self, text: str) -> List[str]:
        """Токенизация текста (безопасно для больших документов)."""
        if not text:
            return []
        # Для больших текстов избегаем spaCy-пайплайна: это главная причина E088/памяти.
        if len(text) > self.spacy_safe_max_chars or not self.nlp:
            return list(self._iter_tokens_regex(text))

        # make_doc делает только токенизацию, без тяжелых компонентов пайплайна
        doc = self.nlp.make_doc(text)
        return [t.text for t in doc]
    
    def lemmatize(self, text: str) -> List[str]:
        """Лемматизация текста"""
        if self.morph:
            tokens = self.tokenize(text)
            lemmas = []
            for token in tokens:
                parsed = self.morph.parse(token)[0]
                lemmas.append(parsed.normal_form)
            return lemmas
        elif self.nlp:
            # spaCy-лемматизация на очень длинных строках дорогая и может падать по памяти,
            # поэтому ограничиваемся "безопасной" длиной.
            sample = text[:self.spacy_safe_max_chars]
            doc = self.nlp(sample)
            return [token.lemma_ for token in doc]
        else:
            return self.tokenize(text)
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Извлечение именованных сущностей из текста"""
        entities = {
            'laws': [],
            'articles': [],
            'dates': [],
            'terms': []
        }
        
        # Извлечение ссылок на законы
        law_patterns = [
            r'(?:Федеральный\s+)?закон\s+(?:от\s+)?(?:\d+\.\d+\.\d+)?\s*№\s*(\d+[-ФЗфз]*)',
            r'(?:ГК|УК|ТК|НК)\s+РФ',
            r'Конституция\s+РФ'
        ]
        
        for pattern in law_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities['laws'].append(match.group(0))
        
        # Извлечение ссылок на статьи
        article_patterns = [
            r'статья\s+(\d+(?:\.\d+)?)',
            r'ст\.\s*(\d+(?:\.\d+)?)',
            r'пункт\s+(\d+)'
        ]
        
        for pattern in article_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities['articles'].append(match.group(1))
        
        # Извлечение дат
        date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
        dates = re.findall(date_pattern, text)
        entities['dates'] = list(set(dates))
        
        # Извлечение терминов (spaCy) — только на "безопасном" объеме текста
        if self.nlp and self.config.get('enable_pos_tagging', True):
            sample = text if len(text) <= self.spacy_safe_max_chars else text[:self.spacy_safe_max_chars]
            try:
                doc = self.nlp(sample)
                # Ищем существительные, которые могут быть терминами
                terms = [token.text for token in doc if token.pos_ == 'NOUN' and token.is_title]
                entities['terms'] = list(set(terms))
            except Exception as e:
                # не валим загрузку документа из-за терминов
                logger.warning(f"Не удалось извлечь термины через spaCy: {e}")
        
        return entities
    
    def extract_references(self, text: str) -> List[Dict]:
        """Извлечение ссылок на другие правовые акты"""
        references = []
        
        # Паттерны для ссылок
        patterns = [
            (r'в\s+соответствии\s+с\s+(.+?)(?:\.|,|;|$)', 'соответствие'),
            (r'согласно\s+(.+?)(?:\.|,|;|$)', 'согласно'),
            (r'в\s+силу\s+(.+?)(?:\.|,|;|$)', 'сила'),
            (r'на\s+основании\s+(.+?)(?:\.|,|;|$)', 'основание'),
        ]
        
        for pattern, ref_type in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ref_text = match.group(1).strip()
                references.append({
                    'type': ref_type,
                    'text': ref_text,
                    'position': match.start()
                })
        
        return references
    
    def extract_structural_elements(self, text: str) -> Dict:
        """Извлечение структурных элементов документа"""
        elements = {
            'chapters': [],
            'articles': [],
            'paragraphs': []
        }
        
        # Поиск глав
        chapter_pattern = r'Глава\s+(\d+)\s*[\.\-]?\s*(.*?)(?=Глава\s+\d+|Статья\s+\d+|$)'
        chapters = re.finditer(chapter_pattern, text, re.IGNORECASE | re.DOTALL)
        for match in chapters:
            elements['chapters'].append({
                'number': match.group(1),
                'title': match.group(2).strip()[:100]  # Первые 100 символов
            })
        
        # Поиск статей
        article_pattern = r'Статья\s+(\d+(?:\.\d+)?)\.?\s*(.*?)(?=Статья\s+\d+|$)'
        articles = re.finditer(article_pattern, text, re.IGNORECASE | re.DOTALL)
        for match in articles:
            elements['articles'].append({
                'number': match.group(1),
                'text': match.group(2).strip()
            })
        
        return elements
    
    def find_key_terms(self, text: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """Найти ключевые термины в тексте"""
        if not text:
            return []

        # Чтобы не считать по мегабайтам текста бесконечно долго — ограничиваем объём
        sample = text if len(text) <= self.key_terms_max_chars else text[:self.key_terms_max_chars]

        # Фильтрация стоп-слов
        stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'к', 'из', 'о', 'а', 'как', 'что', 'это'}

        term_freq: Counter[str] = Counter()
        if self.morph:
            for tok in self._iter_tokens_regex(sample):
                if len(tok) <= 3 or tok in stop_words:
                    continue
                try:
                    lemma = self.morph.parse(tok)[0].normal_form
                except Exception:
                    lemma = tok
                if len(lemma) <= 3 or lemma in stop_words:
                    continue
                term_freq[lemma] += 1
        else:
            # fallback без морфологии
            for tok in self._iter_tokens_regex(sample):
                if len(tok) <= 3 or tok in stop_words:
                    continue
                term_freq[tok] += 1

        return term_freq.most_common(top_n)

