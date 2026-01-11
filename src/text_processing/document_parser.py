"""Модуль для парсинга правовых документов из различных форматов"""
from pathlib import Path
from typing import Dict, List, Optional
import logging
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger(__name__)

class DocumentParser:
    """Класс для парсинга правовых документов"""
    
    def __init__(self):
        self.supported_formats = ['xml', 'html', 'pdf', 'txt']
    
    def parse(self, file_path: Path) -> Dict:
        """Парсить документ в зависимости от формата"""
        suffix = file_path.suffix.lower().lstrip('.')
        
        if suffix not in self.supported_formats:
            raise ValueError(f"Неподдерживаемый формат: {suffix}")
        
        if suffix == 'xml' or suffix == 'html':
            return self._parse_xml_html(file_path)
        elif suffix == 'pdf':
            return self._parse_pdf(file_path)
        elif suffix == 'txt':
            return self._parse_txt(file_path)
    
    def _parse_xml_html(self, file_path: Path) -> Dict:
        """Парсить XML/HTML документ"""
        if BeautifulSoup is None:
            raise ImportError("BeautifulSoup4 не установлен")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'lxml')
        
        # Извлечение метаданных
        title = soup.find('title')
        title_text = title.get_text() if title else file_path.stem
        
        # Поиск структуры документа
        chapters = []
        articles = []
        
        # Попытка найти главы и статьи по различным паттернам
        for chapter_elem in soup.find_all(['chapter', 'глава', 'div'], class_=re.compile(r'chapter|глава', re.I)):
            chapter_num = chapter_elem.get('number') or chapter_elem.get('id', '')
            chapter_title = chapter_elem.find(['title', 'h2', 'h3'])
            chapter_text = chapter_title.get_text() if chapter_title else ''
            
            chapters.append({
                'number': chapter_num,
                'title': chapter_text,
                'text': chapter_elem.get_text()
            })
        
        for article_elem in soup.find_all(['article', 'статья', 'div'], class_=re.compile(r'article|статья', re.I)):
            article_num = article_elem.get('number') or article_elem.get('id', '')
            article_text = article_elem.get_text()
            
            articles.append({
                'number': article_num,
                'text': article_text
            })
        
        return {
            'title': title_text,
            'chapters': chapters,
            'articles': articles,
            'full_text': soup.get_text()
        }
    
    def _parse_pdf(self, file_path: Path) -> Dict:
        """Парсить PDF документ"""
        if pdfplumber is None:
            raise ImportError("pdfplumber не установлен")
        
        text_content = []
        page_texts: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                page_texts.append(page_text)
                text_content.append(page_text)
        
        full_text = '\n'.join(text_content)
        
        # Простая эвристика для извлечения статей
        articles = self._extract_articles_from_text(full_text)

        # Определяем страницу начала статьи (где встречается заголовок "Статья N")
        page_map = self.build_article_page_map_from_pdf_text(page_texts)
        for a in articles:
            num = a.get('number')
            if num and num in page_map:
                a['page'] = page_map[num]
        
        return {
            'title': file_path.stem,
            'chapters': [],
            'articles': articles,
            'full_text': full_text
        }

    def build_article_page_map_from_pdf_text(self, page_texts: List[str]) -> Dict[str, int]:
        """
        Построить отображение {номер_статьи -> номер_страницы} по распознанному тексту PDF.
        Ищем заголовки статей в начале строки, чтобы не ловить ссылки вида "по ст. 55".
        """
        page_map: Dict[str, int] = {}
        header_re = re.compile(r'^\s*Статья\s+(\d+(?:\.\d+)?)\b', re.IGNORECASE | re.MULTILINE)

        for idx, text in enumerate(page_texts, start=1):
            if not text:
                continue
            for m in header_re.finditer(text):
                num = m.group(1)
                # первая встреча — страница начала
                page_map.setdefault(num, idx)

        return page_map

    def find_article_page_in_pdf(self, file_path: Path, article_number: str) -> Optional[int]:
        """Найти страницу, где начинается конкретная статья (для PDF)."""
        if pdfplumber is None:
            return None
        header_re = re.compile(r'^\s*Статья\s+%s\b' % re.escape(article_number), re.IGNORECASE | re.MULTILINE)
        with pdfplumber.open(file_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ''
                if header_re.search(text):
                    return idx
        return None
    
    def _parse_txt(self, file_path: Path) -> Dict:
        """Парсить текстовый файл"""
        with open(file_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
        
        articles = self._extract_articles_from_text(full_text)
        
        return {
            'title': file_path.stem,
            'chapters': [],
            'articles': articles,
            'full_text': full_text
        }
    
    def _extract_articles_from_text(self, text: str) -> List[Dict]:
        """Извлечь статьи из текста по паттернам"""
        articles = []
        
        # Паттерн для поиска статей: "Статья 1.", "Статья 1.1", "Статья 123" и т.д.
        pattern = r'Статья\s+(\d+(?:\.\d+)?)\.?\s*(.*?)(?=Статья\s+\d+|$)'
        
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            article_num = match.group(1)
            article_text = match.group(2).strip()
            
            articles.append({
                'number': article_num,
                'text': article_text
            })
        
        return articles

