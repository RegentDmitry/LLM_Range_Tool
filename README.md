# LLM Range Tool - RAG система для GTO решений PLO4/PLO5

Прототип RAG (Retrieval-Augmented Generation) системы для работы с базой данных GTO решений для Omaha (PLO4/PLO5).

## Описание

Система позволяет на основе текстового вопроса находить подходящие GTO деревья решений в базе данных, которая содержит:
- 317 деревьев для PLO4
- 83 дерева для PLO5
- Покрытие: Cash, MTT, ICM, Exploitative стратегии
- Различные форматы: Heads-Up, 6-Max, с ante, straddle и т.д.

## Структура проекта

```
├── config/                           # Конфигурация AWS
│   ├── credentialsprivate.default.py # Шаблон для credentials
│   └── credentialsprivate.py         # ⚠️  Ваши AWS credentials (не коммитится!)
├── lib/                              # Библиотеки для работы с данными
│   └── boto3_utils.py                # Утилиты для S3 и DynamoDB
├── models/                           # Pydantic модели
│   └── preflop_models.py             # Модели для RAG системы
├── temp/                             # Локальные данные (не коммитятся)
│   ├── preflop-tree-dev.json         # PLO4 деревья (317)
│   ├── 5card-preflop-tree-dev.json   # PLO5 деревья (83)
│   └── tree-tags-dev.json            # Справочник тегов
├── main.py                           # Основной скрипт
└── README_PREFLOP_MODELS.md          # Документация по моделям
```

## Быстрый старт

### 1. Настройка credentials

Скопируйте шаблон и заполните ваши AWS credentials:

```bash
cp config/credentialsprivate.default.py config/credentialsprivate.py
```

Отредактируйте `config/credentialsprivate.py`:

```python
AwsAccessKey = 'ваш-aws-access-key'
AwsSecret = 'ваш-aws-secret'
AwsRegion = 'eu-central-1'
```

### 2. Установка зависимостей

```bash
pip install boto3 pydantic pydantic-ai
```

### 3. Использование

```python
from models import PreflopTree, PreflopQuery, parse_tree_from_dynamodb
from lib import get_dynamodb_record
import json

# Работа с локальными данными
with open('temp/preflop-tree-dev.json', 'r') as f:
    trees_data = json.load(f)

trees = [parse_tree_from_dynamodb(item) for item in trees_data]

# Пример поиска
query = PreflopQuery(
    game_type="plo4",
    number_of_players=6,
    stack_size=100,
    max_results=10
)

# Ваша RAG логика здесь...
```

## AWS Ресурсы

### DynamoDB таблицы:
- `preflop-tree-dev` - деревья PLO4
- `5card-preflop-tree-dev` - деревья PLO5
- `tree-tags-dev` - справочник тегов

### S3 Buckets:

**Деревья (JSON):**
- PLO4: `preflop-trees`
- PLO5: `plo5-preflop-trees`

**Preflop Ranges:**
- PLO4: `postflop-ranges-json`
- PLO5: `plo5-preflop-ranges`

## Документация

Подробная документация по моделям: [README_PREFLOP_MODELS.md](README_PREFLOP_MODELS.md)

## Безопасность

⚠️ **ВАЖНО:** Никогда не коммитьте файл `config/credentialsprivate.py` в git!

Файл уже добавлен в `.gitignore`, но всегда проверяйте перед коммитом:

```bash
git status --ignored
```

## Разработка

Для локальной разработки без AWS можно использовать JSON файлы из папки `temp/`.

## Лицензия

Private project
