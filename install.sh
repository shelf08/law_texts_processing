#!/bin/bash

echo "Обновление pip..."
python -m pip install --upgrade pip

echo ""
echo "Установка зависимостей..."
python -m pip install --upgrade pip setuptools wheel

echo ""
echo "Установка пакетов из requirements.txt..."
python -m pip install -r requirements.txt

echo ""
echo "Установка модели spaCy для русского языка..."
python -m spacy download ru_core_news_sm

echo ""
echo "Установка завершена!"

