"""Скрипт для запуска веб-приложения"""
from src.web.app import app
from src.config import CONFIG

if __name__ == '__main__':
    print(f"Запуск веб-сервера на http://{CONFIG['web']['host']}:{CONFIG['web']['port']}")
    app.run(
        host=CONFIG['web']['host'],
        port=CONFIG['web']['port'],
        debug=CONFIG['web']['debug']
    )

