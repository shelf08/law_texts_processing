"""
Create a new PPTX presentation for the ПравоНавт diploma thesis (8th semester).
Uses the existing PPTX as a structural template, replacing slide content.
No external dependencies beyond standard library.
"""
import zipfile
import re
import shutil
import os
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
SRC = Path(r'C:\Users\shelf\OneDrive\Рабочий стол\ВКР\Лобцов_Д_А_Презентация_НИР_7_сем.pptx')
DST = Path(r'C:\Users\shelf\OneDrive\Рабочий стол\ВКР\Лобцов_Д_А_Презентация_НИР_8_сем.pptx')

# ── XML namespaces ─────────────────────────────────────────────────────────────
NS_A  = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R  = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P  = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

# ── layout refs ───────────────────────────────────────────────────────────────
LAYOUT_TITLE   = "../slideLayouts/slideLayout2.xml"  # title/end slide
LAYOUT_CONTENT = "../slideLayouts/slideLayout1.xml"  # content slide

TNRP = 'panose="02020603050405020304" pitchFamily="18" charset="0"'
TNR  = f'<a:latin typeface="Times New Roman" {TNRP}/><a:cs typeface="Times New Roman" {TNRP}/>'


def rpr(sz, bold=False, color=None):
    """Run properties string."""
    b = ' b="1"' if bold else ''
    parts = [f'<a:rPr lang="ru-RU" sz="{sz}"{b} dirty="0">']
    if color:
        parts.append(f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>')
    parts.append(TNR)
    parts.append('</a:rPr>')
    return ''.join(parts)


def run(text, sz, bold=False, color=None):
    return f'{rpr(sz, bold, color)}<a:t>{text}</a:t>'


def para(runs_xml, align='l', spacing_pct=120, indent=0, space_before=0):
    """Paragraph wrapper."""
    ind = f' marL="{indent}"' if indent else ''
    spc = f'<a:lnSpc><a:spcPct val="{spacing_pct}000"/></a:lnSpc>' if spacing_pct else ''
    sb  = f'<a:spcBef><a:spcPts val="{space_before}"/></a:spcBef>' if space_before else ''
    return f'<a:p><a:pPr algn="{align}"{ind}>{spc}{sb}</a:pPr>{runs_xml}</a:p>'


def textbox(sp_id, x, y, cx, cy, paragraphs_xml, wrap='square'):
    return f'''<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="{sp_id}" name="TextBox{sp_id}"/>
    <p:cNvSpPr txBox="1"/>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="{wrap}"><a:spAutoFit/></a:bodyPr>
    <a:lstStyle/>
    {paragraphs_xml}
  </p:txBody>
</p:sp>'''


def rect_fill(sp_id, x, y, cx, cy, fill_color, text_xml=''):
    """Colored rectangle (for accent bars etc.)"""
    return f'''<p:sp>
  <p:nvSpPr>
    <p:cNvPr id="{sp_id}" name="Rect{sp_id}"/>
    <p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
    <p:nvPr/>
  </p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="{fill_color}"/></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/>{text_xml}</p:txBody>
</p:sp>'''


def slide_xml(shapes_xml, layout_path):
    rels_id = "rId1"
    slide = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {shapes_xml}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''
    rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_REL}">
  <Relationship Id="{rels_id}"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
    Target="{layout_path}"/>
</Relationships>'''
    return slide, rels


# ── slide content definitions ──────────────────────────────────────────────────
W = 12192000   # slide width EMU
H = 6858000    # slide height EMU

UNIV = ('МИНОБРНАУКИ РОССИИ\nФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ ОБРАЗОВАТЕЛЬНОЕ '
        'УЧРЕЖДЕНИЕ ВЫСШЕГО ОБРАЗОВАНИЯ «ВОРОНЕЖСКИЙ ГОСУДАРСТВЕННЫЙ УНИВЕРСИТЕТ» '
        '(ФГБОУ ВО «ВГУ»)\nФакультет компьютерных наук\nКафедра информационных систем')
TITLE_MAIN = 'Обработка и систематизация юридических текстов с помощью онтологий для автоматической навигации по правовым актам'
AUTHOR_LINE = 'Обучающийся: Лобцов Д.А.      Руководитель: к.и.н., доцент Борисова А.А.'


def s_title_or_end(slide_num):
    """Slides 1 and 13 — title/end design."""
    # blue top bar
    bar = rect_fill(2, 0, 0, W, 320000, '1F4E79')
    # University text (top)
    univ_lines = UNIV.replace('\n', '</a:t></a:r><a:br>' + rpr(1400) + '<a:r>' + rpr(1400))
    univ_box = textbox(3, 400000, 350000, W - 800000, 900000,
        para(f'<a:r>{run(UNIV, 1400)}</a:r>', align='ctr', spacing_pct=115))
    # Main title
    title_box = textbox(4, 400000, 1400000, W - 800000, 2000000,
        para(f'<a:r>{run(TITLE_MAIN, 2800, bold=True, color="1F4E79")}</a:r>',
             align='ctr', spacing_pct=120))
    # Decorative blue line
    line = rect_fill(5, 1000000, 3550000, W - 2000000, 18000, '2E74B5')
    # Author
    author_box = textbox(6, 400000, 3650000, W - 800000, 500000,
        para(f'<a:r>{run(AUTHOR_LINE, 2000)}</a:r>', align='ctr'))
    # Year
    year_box = textbox(7, W - 2000000, 4400000, 1600000, 400000,
        para(f'<a:r>{run("2025", 2000)}</a:r>', align='r'))
    # Slide number (hidden on title, shown on end)
    num_text = '' if slide_num == 1 else str(slide_num)
    num_box = textbox(8, W - 900000, H - 600000, 700000, 400000,
        para(f'<a:r>{run(num_text, 1800)}</a:r>', align='r'))

    shapes = '\n'.join([bar, univ_box, title_box, line, author_box, year_box, num_box])
    return slide_xml(shapes, LAYOUT_TITLE)


def s_content(slide_num, heading, items, note=None, two_col=None):
    """
    Standard content slide.
    items: list of (text, is_bullet, indent_level)  OR list of strings
    two_col: (left_items, right_items) for two-column layout
    """
    # blue accent bar top
    bar = rect_fill(2, 0, 0, W, 220000, '1F4E79')
    # slide number bottom right
    num_box = textbox(20, W - 900000, H - 500000, 700000, 380000,
        para(f'<a:r>{run(str(slide_num), 1800)}</a:r>', align='r'))

    # Heading
    head_box = textbox(3, 350000, 260000, W - 700000, 700000,
        para(f'<a:r>{run(heading, 3200, bold=True, color="1F4E79")}</a:r>',
             align='l', spacing_pct=100))
    # Separator line
    sep = rect_fill(4, 350000, 960000, W - 700000, 15000, '2E74B5')

    shapes_list = [bar, head_box, sep, num_box]

    if two_col:
        # Two-column layout
        left_items, right_items = two_col
        col_w = (W - 1000000) // 2
        left_xml  = _items_xml(left_items,  start_id=10)
        right_xml = _items_xml(right_items, start_id=15)
        left_box  = textbox(10, 350000,  1050000, col_w - 100000, H - 1500000,
                            left_xml)
        right_box = textbox(15, 350000 + col_w + 100000, 1050000, col_w - 100000, H - 1500000,
                            right_xml)
        shapes_list += [left_box, right_box]
    elif items:
        # Single column bullet list
        content_xml = _items_xml(items, start_id=10)
        content_box = textbox(5, 350000, 1050000, W - 700000, H - 1600000, content_xml)
        shapes_list.append(content_box)

    if note:
        note_box = textbox(19, 350000, H - 720000, W - 700000, 350000,
            para(f'<a:r>{run(note, 1400, color="595959")}</a:r>', align='l'))
        shapes_list.append(note_box)

    shapes = '\n'.join(shapes_list)
    return slide_xml(shapes, LAYOUT_CONTENT)


def _items_xml(items, start_id=10):
    """Convert list of items to paragraph XML."""
    paras = []
    for item in items:
        if isinstance(item, str):
            # plain line
            text, level, bold, color = item, 0, False, None
        else:
            # tuple: (text, level=0, bold=False, color=None)
            parts = item + (None,) * (4 - len(item))
            text, level, bold, color = parts[0], parts[1] or 0, parts[2] or False, parts[3]

        indent = level * 457200
        bullet_char = '•  ' if level == 0 else '–  '
        sz = 2400 - level * 200
        if text == '':
            paras.append('<a:p><a:pPr/><a:endParaRPr lang="ru-RU"/></a:p>')
        else:
            txt_run = f'<a:r>{run(bullet_char + text, sz, bold=bold, color=color)}</a:r>'
            paras.append(para(txt_run, align='l', spacing_pct=115, indent=indent,
                              space_before=80 if level == 0 else 0))
    return '\n'.join(paras)


# ── define all slides ──────────────────────────────────────────────────────────

SLIDES = []

# 1 – Title
SLIDES.append(s_title_or_end(1))

# 2 – Цель и задачи
SLIDES.append(s_content(2,
    'Цель и задачи',
    [
        ('Цель — разработать систему ПравоНавт для навигации по правовым актам', 0, True, '1F4E79'),
        ('на основе OWL-онтологии и семантического поиска.', 0),
        '',
        ('Реализованные задачи:', 0, True),
        ('Спроектировать OWL-онтологию (классы: Закон, Глава, Статья, Термин; '
         'связи: belongsToLaw, references, definesTerm)', 0),
        ('Реализовать парсер документов: PDF, XML, TXT, DOCX, HTML', 0),
        ('Выполнить NLP-аннотирование: spaCy, pymorphy2, лемматизация, '
         'извлечение сущностей (законы, статьи, даты)', 0),
        ('Реализовать семантический поиск: sentence-transformers + SQLite + '
         'SPARQL keyword fallback', 0),
        ('Реализовать извлечение и запись межстатейных ссылок в онтологию '
         '(ГК, УК, ТК РФ и др.)', 0),
        ('Разработать веб-интерфейс: загрузка, поиск, просмотр, '
         'граф онтологии (D3.js), сценарий навигации по ссылкам', 0),
    ]
))

# 3 – Актуальность
SLIDES.append(s_content(3,
    'Актуальность',
    [
        ('Рост объёма нормативных актов — навигация без системы затруднена', 0),
        ('Полнотекстовый поиск недостаточен: статьи содержат множество '
         'перекрёстных ссылок и специальных терминов', 0),
        ('Цифровизация права и развитие LegalTech требуют семантических '
         'моделей (онтологий) для структурированного доступа к знаниям', 0),
        ('OWL-онтологии позволяют формализовать правовые понятия и связи, '
         'обеспечивая возможность SPARQL-запросов', 0),
    ]
))

# 4 – Архитектура
SLIDES.append(s_content(4,
    'Архитектура системы',
    None,
    two_col=(
        [
            ('Серверная часть (Python / Flask):', 0, True),
            ('DocumentParser — PDF/XML/TXT/DOCX/HTML', 0),
            ('NLP Pipeline — spaCy ru_core_news_sm, pymorphy2', 0),
            ('OntologyManager — rdflib, SPARQL', 0),
            ('SemanticSearch — sentence-transformers, SQLite', 0),
            ('Flask REST API — 15+ эндпоинтов', 0),
            '',
            ('Хранение данных:', 0, True),
            ('OWL/RDF онтология (XML/RDF)', 0),
            ('SQLite — история, эмбеддинги, метаданные', 0),
        ],
        [
            ('Клиентская часть (Jinja2 + JS):', 0, True),
            ('index.html — загрузка, поиск, история', 0),
            ('document.html — просмотр статей, сущности, термины', 0),
            ('graph.html — D3.js граф онтологии', 0),
            '',
            ('Форматы входных данных:', 0, True),
            ('PDF (pdfplumber)', 0),
            ('XML (ElementTree / BeautifulSoup)', 0),
            ('TXT, DOCX (python-docx), HTML', 0),
        ]
    )
))

# 5 – Онтология
SLIDES.append(s_content(5,
    'OWL-онтология правовых актов',
    None,
    two_col=(
        [
            ('Классы:', 0, True, '1F4E79'),
            ('Law — правовой акт (hasTitle, hasDate)', 0),
            ('Chapter — глава закона (hasNumber, hasTitle)', 0),
            ('Article — статья (hasNumber, hasText, hasPage)', 0),
            ('Term — правовой термин (hasTitle)', 0),
            '',
            ('Иерархия:', 0, True, '1F4E79'),
            ('Law → containsChapter → Chapter', 0),
            ('Chapter → containsArticle → Article', 0),
            ('Article → belongsToLaw → Law', 0),
        ],
        [
            ('Свойства связей:', 0, True, '1F4E79'),
            ('references — ссылка статьи на статью', 0),
            ('referencesLaw — ссылка на другой закон', 0),
            ('definesTerm — определение термина', 0),
            ('usesTerm — использование термина', 0),
            '',
            ('Технологии:', 0, True, '1F4E79'),
            ('rdflib 7.6, формат RDF/XML', 0),
            ('SPARQL-запросы через OntologyManager', 0),
            ('Автоматическая «санитизация» файла', 0),
        ]
    )
))

# 6 – Обработка документов
SLIDES.append(s_content(6,
    'Обработка документов — пайплайн',
    [
        ('1. Загрузка файла (PDF / XML / TXT / DOCX / HTML) через веб-форму', 0),
        ('2. DocumentParser — разбиение на главы и статьи; '
         'извлечение номеров, заголовков, текста, страниц', 0),
        ('3. OntologyManager — запись Law → Chapter → Article в RDF-граф', 0),
        ('4. NLP Pipeline (spaCy + pymorphy2):', 0),
        ('лемматизация и стоп-слова; распознавание именованных сущностей '
         '(законы, статьи, даты)', 1),
        ('извлечение правовых терминов → Term + definesTerm / usesTerm', 1),
        ('извлечение межстатейных ссылок → Article.references', 1),
        ('5. SemanticSearch — векторизация текста статей '
         '(sentence-transformers paraphrase-multilingual-MiniLM-L12-v2), '
         'сохранение эмбеддингов в SQLite', 0),
        ('6. Прогресс-бар в реальном времени через SSE (Server-Sent Events)', 0),
    ]
))

# 7 – Семантический поиск
SLIDES.append(s_content(7,
    'Семантический поиск',
    [
        ('Двухуровневый поиск по запросу пользователя:', 0, True),
        ('Уровень 1 — семантический: cosine similarity по эмбеддингам '
         '(sentence-transformers), SQL-запрос к SQLite', 0),
        ('Уровень 2 — ключевой: SPARQL по тексту статей '
         '(CONTAINS + REGEX fallback для составных запросов)', 0),
        ('Уровень 3 — по терминам: SPARQL-поиск по Term.hasTitle '
         '+ definesTerm / usesTerm', 0),
        '',
        ('Результаты поиска:', 0, True),
        ('Релевантность (score) от 0 до 100%', 0),
        ('Название статьи, номер, краткий контекст (150 символов)', 0),
        ('Быстрый переход к полному тексту статьи', 0),
        ('История поиска сохраняется в SQLite', 0),
    ]
))

# 8 – Веб-интерфейс загрузка
SLIDES.append(s_content(8,
    'Веб-интерфейс — загрузка и история документов',
    [
        ('Единый экран index.html:', 0, True),
        ('Glassmorphism-навигация с брендом «ПравоНавт»', 0),
        ('Drag-and-drop зона загрузки + click-to-select', 0),
        ('Прогресс-бар с этапами обработки (Server-Sent Events)', 0),
        ('Карточки истории загрузок с фильтрацией по типу файла', 0),
        ('Поиск по загруженным документам', 0),
        '',
        ('Поддерживаемые форматы:', 0, True),
        ('PDF — Гражданский, Уголовный, Трудовой, Налоговый кодекс, КоАП и др.', 0),
        ('XML (Garant/Consultant) — структурированные выгрузки', 0),
        ('DOCX, TXT, HTML — дополнительные источники', 0),
    ]
))

# 9 – Веб-интерфейс просмотр
SLIDES.append(s_content(9,
    'Веб-интерфейс — просмотр документа и навигация',
    [
        ('Страница document.html:', 0, True),
        ('Хлебные крошки и название документа в навигации', 0),
        ('Полный текст статьи с подсветкой сущностей', 0),
        ('Боковая панель с тремя секциями:', 0),
        ('Сущности (NER): законы (синий), статьи (зелёный), даты (фиолетовый)', 1),
        ('Термины с частотой встречаемости', 1),
        ('Перекрёстные ссылки: исходящие и входящие (сценарий 4.4)', 1),
        ('Быстрые ссылки для перехода к связанным статьям', 0),
        '',
        ('Сценарий навигации 4.4 — поиск → статья → связанные акты:', 0, True),
        ('Результаты поиска → клик → просмотр статьи '
         '→ панель ссылок «Эта статья ссылается на» / «На эту статью ссылаются»', 0),
    ]
))

# 10 – Граф онтологии
SLIDES.append(s_content(10,
    'Граф онтологии — D3.js визуализация',
    [
        ('Интерактивный граф force-directed (D3.js v7) на странице graph.html:', 0, True),
        ('Три типа узлов: Закон (синий), Статья (зелёный), Термин (жёлтый)', 0),
        ('Визуальные эффекты: glow-фильтр (SVG feGaussianBlur), dot-grid фон', 0),
        ('Glassmorphism-панель статистики: количество узлов и связей', 0),
        ('Фильтрация по типу закона и типу узлов', 0),
        ('Зум, перетаскивание, тултипы с деталями узла', 0),
        '',
        ('API для графа:', 0, True),
        ('GET /api/graph — возвращает nodes[] и links[] из онтологии', 0),
        ('Поддерживает до 1000+ узлов с группировкой по закону', 0),
    ]
))

# 11 – Сценарий 4.4
SLIDES.append(s_content(11,
    'Сценарий 4.4 — навигация по перекрёстным ссылкам',
    [
        ('Задача:', 0, True, '1F4E79'),
        ('Пользователь находит статью → видит, на какие статьи она ссылается '
         'и какие статьи ссылаются на неё', 0),
        '',
        ('Реализация в NLP-пайплайне:', 0, True, '1F4E79'),
        ('Регулярное выражение: «статье» / «статьей» + номер', 0),
        ('Определение закона по аббревиатуре в радиусе 80 символов '
         '(ГК, УК, ТК, НК, КоАП, КАС, ГПК, АПК и др.)', 0),
        ('Запись в онтологию: Article → law:references → Article', 0),
        ('Межзаконные ссылки: Article → law:referencesLaw → Law', 0),
        '',
        ('API и отображение:', 0, True, '1F4E79'),
        ('GET /api/document/{id}/article/{num}/related → outgoing/incoming', 0),
        ('Боковая панель в document.html — группы «Ссылается на» / «Ссылаются»', 0),
    ]
))

# 12 – Результаты
SLIDES.append(s_content(12,
    'Результаты и выводы',
    [
        ('Разработана и реализована система ПравоНавт:', 0, True, '1F4E79'),
        ('OWL-онтология с 4 классами и 10+ свойствами', 0),
        ('Парсер 5 форматов документов (PDF, XML, DOCX, TXT, HTML)', 0),
        ('NLP-пайплайн: NER, лемматизация, термины, ссылки', 0),
        ('Двухуровневый поиск: семантический + SPARQL', 0),
        ('Граф онтологии с D3.js (интерактивная визуализация)', 0),
        ('Сценарий навигации по перекрёстным ссылкам (сценарий 4.4)', 0),
        '',
        ('Перспективы развития:', 0, True, '595959'),
        ('Интеграция внешних источников (КонсультантПлюс, Гарант)', 0),
        ('ML-классификация правовых категорий', 0),
        ('Расширение поддерживаемых форматов и кодексов', 0),
    ]
))

# 13 – End title
SLIDES.append(s_title_or_end(13))


# ── build PPTX ────────────────────────────────────────────────────────────────

def build_presentation_xml(n_slides):
    """Generate ppt/presentation.xml with n_slides references."""
    slide_ids = '\n'.join(
        f'<p:sldId id="{260 + i}" r:id="rId{i + 1}"/>'
        for i in range(1, n_slides + 1)
    )
    rels_non_slides = '\n'.join([
        f'<Relationship Id="rId{n_slides + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>',
        f'<Relationship Id="rId{n_slides + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps" Target="presProps.xml"/>',
        f'<Relationship Id="rId{n_slides + 3}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps" Target="viewProps.xml"/>',
        f'<Relationship Id="rId{n_slides + 4}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>',
        f'<Relationship Id="rId{n_slides + 5}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/tableStyles" Target="tableStyles.xml"/>',
    ])
    pres_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" saveSubsetFonts="1">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId{n_slides + 1}"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
    {slide_ids}
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''

    slide_rels = '\n'.join(
        f'<Relationship Id="rId{i}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
        f'Target="slides/slide{i}.xml"/>'
        for i in range(1, n_slides + 1)
    )
    pres_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_REL}">
  {slide_rels}
  {rels_non_slides}
</Relationships>'''
    return pres_xml, pres_rels


def build_content_types(n_slides):
    slide_overrides = '\n'.join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, n_slides + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/ppt/presentation.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  {slide_overrides}
  <Override PartName="/ppt/presProps.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml"/>
  <Override PartName="/ppt/viewProps.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml"/>
  <Override PartName="/ppt/theme/theme1.xml"
    ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/ppt/tableStyles.xml"
    ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml"/>
</Types>'''


# ── copy template files ────────────────────────────────────────────────────────
COPY_PREFIXES = (
    'ppt/slideMasters/',
    'ppt/slideLayouts/',
    'ppt/theme/',
    'ppt/presProps.xml',
    'ppt/viewProps.xml',
    'ppt/tableStyles.xml',
    '_rels/.rels',
    'docProps/',
)

n = len(SLIDES)
pres_xml, pres_rels = build_presentation_xml(n)
content_types = build_content_types(n)

print(f"Creating PPTX with {n} slides...")

with zipfile.ZipFile(SRC, 'r') as src_zip, \
     zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as dst_zip:

    # Copy template files
    for name in src_zip.namelist():
        if any(name.startswith(p) for p in COPY_PREFIXES):
            dst_zip.writestr(name, src_zip.read(name))

    # Write Content_Types
    dst_zip.writestr('[Content_Types].xml', content_types.encode('utf-8'))

    # Write presentation.xml and its rels
    dst_zip.writestr('ppt/presentation.xml', pres_xml.encode('utf-8'))
    dst_zip.writestr('ppt/_rels/presentation.xml.rels', pres_rels.encode('utf-8'))

    # Write slides
    for idx, (s_xml, s_rels) in enumerate(SLIDES, start=1):
        dst_zip.writestr(f'ppt/slides/slide{idx}.xml', s_xml.encode('utf-8'))
        dst_zip.writestr(f'ppt/slides/_rels/slide{idx}.xml.rels', s_rels.encode('utf-8'))

print(f"Done! Saved to: {DST}")
print(f"File size: {DST.stat().st_size:,} bytes")
