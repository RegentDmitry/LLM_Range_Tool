# Анализ бакетов и построение decision trees

## Выполненные задачи

✅ Скопирована логика бакетирования из проекта `omaha range predictor`
✅ Построены 2 bucket matrices для доски **9s6d5c**
✅ Созданы 6 decision trees с параметром `min_leaf` (1, 10, 50)
✅ Все деревья экспортированы в Mermaid формат

## Структура проекта

```
├── lib/
│   ├── buckets.py          # 85 функций анализа покерных рук
│   ├── card.py             # Классы Card, CardValue, CardSuit
│   ├── data_loader.py      # Загрузка GTO деревьев
│   └── query_agent.py      # AI агент для RAG
├── output/
│   ├── bucket_matrix_lead_9s6d5c.csv       # Матрица 1: Lead ситуация
│   ├── bucket_matrix_nolead_9s6d5c.csv     # Матрица 2: NoLead ситуация
│   ├── tree_lead_9s6d5c_min1.mmd           # Дерево Lead (детальное)
│   ├── tree_lead_9s6d5c_min10.mmd          # Дерево Lead (средняя детализация)
│   ├── tree_lead_9s6d5c_min50.mmd          # Дерево Lead (упрощённое)
│   ├── tree_nolead_9s6d5c_min1.mmd         # Дерево NoLead (детальное)
│   ├── tree_nolead_9s6d5c_min10.mmd        # Дерево NoLead (средняя детализация)
│   └── tree_nolead_9s6d5c_min50.mmd        # Дерево NoLead (упрощённое)
└── build_bucket_matrix.py  # Основной скрипт построения матриц и деревьев
```

## Описание матриц

### Матрица 1: Lead (инициатива)
**Источники данных:**
- `1_2 POT.csv` - 66,550 комбо (бет 1/2 пота)
- `CHECK.csv` - 62,788 комбо (чек)

**Действия:** `bet_1/2pot`, `check`

### Матрица 2: NoLead (без инициативы)
**Источники данных:**
- `NoLead_1_2 POT.csv` - 49,746 комбо (бет 1/2 пота)
- `NoLead_CHECK.csv` - 79,510 комбо (чек)

**Действия:** `bet_1/2pot`, `check`

## Bucket Features (85 признаков)

Каждое комбо анализируется через 85 бинарных признаков:

### Готовые руки (Made Hands)
- Royal Flush, Flush, Straight
- Sets, Two Pair, Top Pair
- Full House, Quads

### Дро (Draws)
- Flush Draw, Backdoor Flush Draw
- Straight Draw, Gutshot, OESD
- Wrap, Double Gutshot

### Блокеры (Blockers)
- Nut Blocker, Flush Blocker
- Straight Draw Blocker
- Top Pair Blocker

### Префлоп характеристики
- Suited, Connected, Paired
- High Card, Gaps

## Decision Trees

Для каждой матрицы построены 3 дерева с разным уровнем детализации:

### min_leaf = 1 (Максимальная детализация)
- **Lead:** 34 KB, ~250+ узлов
- **NoLead:** 37 KB, ~270+ узлов
- Точность: 100% на обучающей выборке
- Использование: Детальный анализ всех нюансов

### min_leaf = 10 (Средняя детализация)
- **Lead:** 12 KB, ~90 узлов
- **NoLead:** 12 KB, ~90 узлов
- Баланс между точностью и простотой
- Использование: Практическая игра

### min_leaf = 50 (Упрощённое)
- **Lead:** 2.3 KB, ~20 узлов
- **NoLead:** 2.6 KB, ~22 узла
- Максимальная читаемость
- Использование: Быстрые решения, обучение

## Как использовать Mermaid диаграммы

### Вариант 1: GitHub/GitLab
Вставьте содержимое `.mmd` файла в markdown:

\`\`\`markdown
\`\`\`mermaid
flowchart TD
    node0{"bucket_64"}
    node0 -->|0| node1
    ...
\`\`\`
\`\`\`

### Вариант 2: Online просмотр
1. Откройте https://mermaid.live
2. Вставьте содержимое `.mmd` файла
3. Экспортируйте в PNG/SVG/PDF

### Вариант 3: VS Code
Установите расширение "Markdown Preview Mermaid Support"

## Запуск скрипта

```bash
# Установка зависимостей
pip install pandas scikit-learn tqdm

# Запуск построения матриц и деревьев
python3 build_bucket_matrix.py
```

Скрипт автоматически:
1. Загружает CSV файлы с диапазонами
2. Бакетирует каждое комбо (85 признаков)
3. Строит агрегированные матрицы
4. Обучает decision trees
5. Экспортирует в Mermaid формат

## Параметры настройки

В `build_bucket_matrix.py` можно изменить:

```python
# Доска
board = '9s6d5c'  # Любая флоп-доска

# Источники данных
range_files = {
    'bet_1/2pot': 'путь/к/файлу.csv',
    'check': 'путь/к/файлу.csv'
}

# Параметр min_leaf для деревьев
for min_leaf in [1, 10, 50]:  # Можно добавить другие значения
    ...
```

## Интерпретация результатов

### Чтение дерева решений

```mermaid
flowchart TD
    node0{"bucket_64"}  --> Проверка признака #64
    node0 -->|0| node1  --> Если признак = 0
    node0 -->|1| node2  --> Если признак = 1
    node3["check"]      --> Листовой узел: рекомендация CHECK
```

### Bucket номера

Признаки нумеруются от 0 до 84:
- `bucket_0` до `bucket_20` - Made hands
- `bucket_21` до `bucket_50` - Draws
- `bucket_51` до `bucket_70` - Blockers
- `bucket_71` до `bucket_84` - Preflop features

Детальная расшифровка в `lib/buckets.py` (строки 1203-1380)

## Производительность

Обработка на доске 9s6d5c:
- **Lead матрица:** 129,338 комбо → обработано за ~3 минуты
- **NoLead матрица:** 129,256 комбо → обработано за ~3 минуты
- **Общее время:** ~6 минут

## Следующие шаги

1. **Анализ деревьев:** Изучить какие признаки наиболее важны для решений
2. **Сравнение Lead vs NoLead:** Найти ключевые различия в стратегиях
3. **Другие доски:** Построить матрицы для разных текстур флопа
4. **Интеграция с RAG:** Использовать деревья для объяснения GTO решений

## Технические детали

### Бакетирование
- Функция: `get_all_buckets(combo, board)`
- Вход: `combo="AsKsQsTs"`, `board="9s6d5c"`
- Выход: массив 85 бинарных признаков `[0, 1, 0, ..., 1]`

### Агрегация
- Группировка по уникальным комбинациям признаков
- Суммирование весов (frequencies) по действиям
- Нормализация к процентам

### Decision Tree
- Алгоритм: sklearn DecisionTreeClassifier
- Критерий: Gini impurity
- Параметр: `min_samples_leaf` (минимум samples в листе)
- Веса: частоты комбо из GTO солвера

---

**Дата создания:** 2025-12-04
**Проект:** LLM Range Tool - RAG система для GTO решений PLO4/PLO5
