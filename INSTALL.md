# Инструкция по установке

## Проблема с компиляцией numpy на Windows

Если вы видите ошибку компиляции numpy (отсутствие компилятора C), это означает, что pip пытается собрать пакет из исходников. Решение - использовать предкомпилированные wheel-пакеты.

## Решение для Python 3.13

### Вариант 1: Автоматическая установка (рекомендуется)

Используйте скрипт установки:

**Windows:**
```cmd
install.bat
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

### Вариант 2: Ручная установка

1. **Обновите pip, setuptools и wheel:**
```cmd
py -m pip install --upgrade pip setuptools wheel
```

2. **Установите numpy отдельно (с предкомпилированным wheel):**
```cmd
py -m pip install numpy --only-binary :all:
```

3. **Установите остальные зависимости:**
```cmd
py -m pip install -r requirements.txt
```

4. **Установите модель spaCy:**
```cmd
py -m spacy download ru_core_news_sm
```

**Примечание:** На Windows используйте `py` вместо `python`

### Вариант 3: Если numpy все еще не устанавливается

Попробуйте установить numpy из предкомпилированных wheel напрямую:

```bash
# Для Python 3.13 (64-bit Windows)
python -m pip install https://files.pythonhosted.org/packages/[путь_к_wheel]/numpy-2.0.0-cp313-cp313-win_amd64.whl

# Или используйте conda (если установлен)
conda install numpy pandas
```

### Вариант 4: Использование conda (альтернатива)

Если проблемы с pip продолжаются, используйте conda:

```bash
conda create -n law_texts python=3.13
conda activate law_texts
conda install numpy pandas
pip install -r requirements.txt
```

## Проверка установки

После установки проверьте:

```python
import numpy
import pandas
import rdflib
import flask
import spacy

print("Все пакеты установлены успешно!")
```

## Устранение проблем

### Ошибка: "Microsoft Visual C++ 14.0 is required"

**Решение:** Установите Microsoft C++ Build Tools:
- Скачайте с https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Или используйте предкомпилированные wheel-пакеты (см. выше)

### Ошибка: "No module named 'numpy'"

**Решение:** 
1. Убедитесь, что используете правильный интерпретатор Python
2. Переустановите numpy: `pip uninstall numpy && pip install numpy`

### Ошибка при установке spaCy модели

**Решение:**
```bash
python -m pip install --upgrade spacy
python -m spacy download ru_core_news_sm
```

## Альтернативные версии пакетов

Если проблемы продолжаются, попробуйте использовать более старые версии:

```bash
pip install numpy==1.26.4 --only-binary :all:
pip install pandas==2.1.4
```

