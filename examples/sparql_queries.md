# Примеры SPARQL-запросов для работы с онтологией правовых актов

## 1. Поиск всех законов

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?law ?title ?date WHERE {
    ?law a law:Law .
    ?law law:hasTitle ?title .
    OPTIONAL { ?law law:hasDate ?date . }
}
ORDER BY ?title
```

## 2. Поиск статей по термину

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?article ?article_number ?term WHERE {
    ?term a law:Term ;
          law:hasTitle ?term_text .
    FILTER(CONTAINS(LCASE(?term_text), LCASE("договор")))
    ?article law:usesTerm ?term ;
             law:hasNumber ?article_number .
}
```

## 3. Поиск статей, определяющих термин

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?article ?article_number ?term_text WHERE {
    ?term a law:Term ;
          law:hasTitle ?term_text .
    ?article law:definesTerm ?term ;
             law:hasNumber ?article_number .
}
```

## 4. Поиск всех ссылок из статьи

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?ref_article ?ref_number WHERE {
    law:law1_article_1 law:references ?ref_article .
    ?ref_article law:hasNumber ?ref_number .
}
```

## 5. Поиск статей, ссылающихся на конкретный закон

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?article ?article_number WHERE {
    ?article law:referencesLaw law:law1 ;
             law:hasNumber ?article_number .
}
```

## 6. Поиск всех статей в главе

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?article ?article_number WHERE {
    law:law1_chapter_1 law:containsArticle ?article .
    ?article law:hasNumber ?article_number .
}
ORDER BY ?article_number
```

## 7. Поиск синонимов термина

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?synonym WHERE {
    {
        law:term_договор law:hasSynonym ?synonym .
    } UNION {
        ?synonym law:hasSynonym law:term_договор .
    }
    ?synonym law:hasTitle ?synonym_text .
}
```

## 8. Поиск статей, связанных через термины

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT DISTINCT ?article1 ?article2 ?term WHERE {
    ?article1 law:usesTerm ?term .
    ?article2 law:usesTerm ?term .
    FILTER(?article1 != ?article2)
    ?term law:hasTitle ?term_text .
}
LIMIT 100
```

## 9. Поиск статей по ключевому слову в тексте

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?article ?article_number ?text WHERE {
    ?article a law:Article ;
             law:hasNumber ?article_number ;
             law:hasText ?text .
    FILTER(CONTAINS(LCASE(?text), LCASE("имущество")))
}
```

## 10. Построение графа связей для визуализации

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?from ?to ?type WHERE {
    {
        ?from law:references ?to .
        BIND("reference" as ?type)
    } UNION {
        ?from law:usesTerm ?to .
        BIND("term" as ?type)
    } UNION {
        ?from law:definesTerm ?to .
        BIND("definition" as ?type)
    } UNION {
        ?from law:containsArticle ?to .
        BIND("contains" as ?type)
    }
}
```

## 11. Поиск статей по правовому институту

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?article ?article_number ?institution WHERE {
    ?article law:belongsToInstitution ?institution ;
             law:hasNumber ?article_number .
    ?institution law:hasTitle ?institution_name .
    FILTER(CONTAINS(LCASE(?institution_name), LCASE("собственность")))
}
```

## 12. Навигация: от термина к статьям к связанным статьям

```sparql
PREFIX law: <http://law.ontology.ru/#>
SELECT ?term ?article1 ?article2 WHERE {
    ?term a law:Term ;
          law:hasTitle "договор" .
    ?article1 law:usesTerm ?term ;
              law:hasNumber ?num1 .
    ?article1 law:references ?article2 .
    ?article2 law:hasNumber ?num2 .
}
```

