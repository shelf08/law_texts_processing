"""Модуль для работы с базой данных истории загрузок документов"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

from src.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

class DocumentHistoryDB:
    """Класс для работы с базой данных истории документов"""
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = PROJECT_ROOT / "data" / "documents.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                law_id TEXT NOT NULL,
                title TEXT,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                entities_count INTEGER DEFAULT 0,
                terms_count INTEGER DEFAULT 0,
                entities_json TEXT,
                terms_json TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(filename, law_id)
            )
        ''')
        
        # Добавляем новые колонки, если их нет (для существующих БД)
        try:
            cursor.execute('ALTER TABLE documents ADD COLUMN entities_json TEXT')
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        
        try:
            cursor.execute('ALTER TABLE documents ADD COLUMN terms_json TEXT')
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        
        conn.commit()
        conn.close()
        logger.info(f"База данных инициализирована: {self.db_path}")
    
    def add_document(self, filename: str, law_id: str, title: str, 
                    file_path: str, file_size: int = None,
                    entities_count: int = 0, terms_count: int = 0,
                    entities: Dict = None, terms: List = None) -> int:
        """Добавить документ в историю"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # Сериализуем entities и terms в JSON
            entities_json = json.dumps(entities, ensure_ascii=False) if entities else None
            terms_json = json.dumps(terms, ensure_ascii=False) if terms else None
            
            # Проверяем, существует ли уже такой документ
            cursor.execute('''
                SELECT id FROM documents 
                WHERE filename = ? AND law_id = ?
            ''', (filename, law_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующую запись
                cursor.execute('''
                    UPDATE documents 
                    SET title = ?, file_path = ?, file_size = ?,
                        entities_count = ?, terms_count = ?,
                        entities_json = ?, terms_json = ?,
                        uploaded_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (title, str(file_path), file_size, entities_count, terms_count, 
                      entities_json, terms_json, existing[0]))
                doc_id = existing[0]
            else:
                # Добавляем новую запись
                cursor.execute('''
                    INSERT INTO documents 
                    (filename, law_id, title, file_path, file_size, entities_count, terms_count, entities_json, terms_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (filename, law_id, title, str(file_path), file_size, entities_count, terms_count, entities_json, terms_json))
                doc_id = cursor.lastrowid
            
            conn.commit()
            logger.info(f"Документ добавлен в историю: {filename} (ID: {doc_id})")
            return doc_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка добавления документа в БД: {e}")
            raise
        finally:
            conn.close()
    
    def get_all_documents(self, limit: int = 100) -> List[Dict]:
        """Получить все документы из истории"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, law_id, title, file_path, file_size,
                   entities_count, terms_count, uploaded_at
            FROM documents
            ORDER BY uploaded_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict]:
        """Получить документ по ID"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, law_id, title, file_path, file_size,
                   entities_count, terms_count, entities_json, terms_json, uploaded_at
            FROM documents
            WHERE id = ?
        ''', (doc_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            doc = dict(row)
            # Десериализуем JSON
            if doc.get('entities_json'):
                try:
                    doc['entities'] = json.loads(doc['entities_json'])
                except:
                    doc['entities'] = {}
            else:
                doc['entities'] = {}
            
            if doc.get('terms_json'):
                try:
                    doc['terms'] = json.loads(doc['terms_json'])
                except:
                    doc['terms'] = []
            else:
                doc['terms'] = []
            
            return doc
        return None
    
    def delete_document(self, doc_id: int) -> bool:
        """Удалить документ из истории"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            logger.info(f"Документ удален из истории: ID {doc_id}")
            return deleted
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка удаления документа: {e}")
            raise
        finally:
            conn.close()

    def get_document_by_law_id(self, law_id: str) -> Optional[Dict]:
        """Получить последний (по uploaded_at) документ по law_id"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, filename, law_id, title, file_path, file_size,
                   entities_count, terms_count, entities_json, terms_json, uploaded_at
            FROM documents
            WHERE law_id = ?
            ORDER BY uploaded_at DESC
            LIMIT 1
        ''', (law_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        doc = dict(row)
        # Десериализуем JSON (по аналогии с get_document_by_id)
        if doc.get('entities_json'):
            try:
                doc['entities'] = json.loads(doc['entities_json'])
            except Exception:
                doc['entities'] = {}
        else:
            doc['entities'] = {}

        if doc.get('terms_json'):
            try:
                doc['terms'] = json.loads(doc['terms_json'])
            except Exception:
                doc['terms'] = []
        else:
            doc['terms'] = []

        return doc

