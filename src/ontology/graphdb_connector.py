"""Модуль для подключения к GraphDB"""
from SPARQLWrapper import SPARQLWrapper, JSON
from typing import List, Dict, Optional
import logging

from src.config import CONFIG

logger = logging.getLogger(__name__)

class GraphDBConnector:
    """Класс для работы с GraphDB через SPARQL"""
    
    def __init__(self):
        self.config = CONFIG['graphdb']
        self.endpoint = f"http://{self.config['host']}:{self.config['port']}/repositories/{self.config['repository']}"
        self.sparql = SPARQLWrapper(self.endpoint)
        
        if self.config.get('username') and self.config.get('password'):
            self.sparql.setCredentials(self.config['username'], self.config['password'])
        
        self.sparql.setReturnFormat(JSON)
        logger.info(f"Подключение к GraphDB: {self.endpoint}")
    
    def execute_query(self, query: str) -> List[Dict]:
        """Выполнить SPARQL-запрос"""
        try:
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()
            
            bindings = results.get('results', {}).get('bindings', [])
            formatted_results = []
            
            for binding in bindings:
                formatted_binding = {}
                for key, value in binding.items():
                    formatted_binding[key] = value.get('value', '')
                formatted_results.append(formatted_binding)
            
            return formatted_results
        except Exception as e:
            logger.error(f"Ошибка выполнения SPARQL-запроса: {e}")
            return []
    
    def upload_rdf(self, rdf_data: str, format: str = "xml"):
        """Загрузить RDF данные в GraphDB"""
        # Для загрузки данных в GraphDB обычно используется REST API
        # Здесь можно добавить реализацию через requests
        pass
    
    def test_connection(self) -> bool:
        """Проверить подключение к GraphDB"""
        try:
            query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"
            self.execute_query(query)
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к GraphDB: {e}")
            return False

