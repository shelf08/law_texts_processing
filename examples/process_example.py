"""Пример использования модулей для обработки правовых документов"""
from pathlib import Path
import logging

from src.integration.document_processor import DocumentProcessor
from src.config import PROJECT_ROOT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Пример обработки документа"""
    processor = DocumentProcessor()
    
    # Путь к примеру документа
    # В реальном использовании замените на путь к вашему документу
    example_doc = PROJECT_ROOT / "data" / "raw" / "example_law.xml"
    
    if not example_doc.exists():
        logger.warning(f"Файл {example_doc} не найден. Создайте пример документа.")
        return
    
    # Обработка документа
    result = processor.process_document(example_doc)
    
    logger.info("Результаты обработки:")
    logger.info(f"  ID закона: {result['law_id']}")
    logger.info(f"  Статей: {result['articles_count']}")
    logger.info(f"  Глав: {result['chapters_count']}")
    logger.info(f"  Терминов: {result['terms_count']}")
    logger.info(f"  Ключевые термины: {[t[0] for t in result['key_terms'][:10]]}")

if __name__ == "__main__":
    main()

