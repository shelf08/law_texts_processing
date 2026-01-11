@echo off
echo Обновление pip...
py -m pip install --upgrade pip

echo.
echo Установка зависимостей...
py -m pip install --upgrade pip setuptools wheel

echo.
echo Установка numpy с предкомпилированными пакетами...
py -m pip install numpy --only-binary :all:

echo.
echo Установка пакетов из requirements.txt...
py -m pip install -r requirements.txt

echo.
echo Установка модели spaCy для русского языка...
py -m spacy download ru_core_news_sm

echo.
echo Установка завершена!
pause

