"""Конфигурация приложения"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Путь к корню проекта
PROJECT_ROOT = Path(__file__).parent.parent

# Загрузка конфигурации из YAML
config_path = PROJECT_ROOT / "config" / "config.yaml"
with open(config_path, 'r', encoding='utf-8') as f:
    CONFIG = yaml.safe_load(f)

# Переопределение из переменных окружения
CONFIG['graphdb']['host'] = os.getenv('GRAPHDB_HOST', CONFIG['graphdb']['host'])
CONFIG['graphdb']['port'] = int(os.getenv('GRAPHDB_PORT', CONFIG['graphdb']['port']))
CONFIG['graphdb']['repository'] = os.getenv('GRAPHDB_REPOSITORY', CONFIG['graphdb']['repository'])
CONFIG['graphdb']['username'] = os.getenv('GRAPHDB_USERNAME', CONFIG['graphdb']['username'])
CONFIG['graphdb']['password'] = os.getenv('GRAPHDB_PASSWORD', CONFIG['graphdb']['password'])

