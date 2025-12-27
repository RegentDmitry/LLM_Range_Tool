# Data Processing Guide

Руководство по работе с данными в RangeLab AI.

## Архитектура данных

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   YouTube/MP4   │────▶│  AssemblyAI      │────▶│  PostgreSQL     │
│   Videos        │     │  Transcription   │     │  + pgvector     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  poker_taxonomy │────▶│  LLM Analysis    │────▶│  Neo4j Aura     │
│  .yaml          │     │  (concepts)      │     │  Knowledge Graph│
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Компоненты

| Компонент | Назначение | Хранение |
|-----------|------------|----------|
| Videos | Метаданные видео | PostgreSQL `videos` |
| Transcripts | Текст + timestamps + embeddings | PostgreSQL `transcripts` |
| Taxonomy | Концепты + синонимы | `data/poker_taxonomy.yaml` |
| Knowledge Graph | Связи видео-концепты | Neo4j Aura (cloud) |

## Конфигурация

### Переменные окружения (.env)

```bash
# OpenAI (embeddings + LLM)
OPENAI_API_KEY=sk-...

# AssemblyAI (транскрипция)
ASSEMBLYAI_API_KEY=...

# Neo4j Aura (граф)
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
NEO4J_DATABASE=neo4j
```

### PostgreSQL (локально)

```python
# lib/conversational_rag.py автоматически определяет хост
DB_CONFIG = {
    "host": "172.24.192.1",  # Windows host из WSL
    "port": 5432,
    "database": "rangelab",
    "user": "postgres",
    "password": "dbpass"
}
```

---

## 1. Добавление новых видео

### Вариант A: Batch Processing (рекомендуется для множества файлов)

Для массовой обработки видео из папки используйте `batch_process_videos.py`:

```bash
# Структура папки:
# /path/to/videos/
#   ├── Video Title 1.mp3
#   ├── Video Title 1.txt   # метаданные
#   ├── Video Title 2.mp3
#   ├── Video Title 2.txt
#   └── ...

# Формат .txt файла метаданных:
# author : AuthorName
# url : https://example.com/lesson/...
# category : postflop plo4

# Dry run - показать что будет обработано
python batch_process_videos.py --folder "/path/to/videos" --dry-run

# Обработка с пропуском уже существующих
python batch_process_videos.py --folder "/path/to/videos"

# Обработка всех (даже существующих)
python batch_process_videos.py --folder "/path/to/videos" --no-skip

# Ограничить количество (для тестов)
python batch_process_videos.py --folder "/path/to/videos" --limit 5
```

**Что делает batch_process_videos.py:**
1. Сканирует папку на MP3 + TXT файлы
2. Транскрибирует каждое видео через AssemblyAI
3. Создаёт embeddings (батчами для скорости) и сохраняет в PostgreSQL
4. Анализирует концепты через LLM:
   - Находит известные концепты из taxonomy
   - **Обнаруживает НОВЫЕ концепты** (автоматически добавляет в `poker_taxonomy.yaml`)
5. Обновляет Neo4j граф (MENTIONS связи + новые концепты)

**Особенности:**
- Параллельная обработка embeddings (batch API)
- Progress bar (tqdm) с текущим статусом
- Автоматическое пополнение taxonomy новыми концептами
- Graceful handling ошибок (продолжает при сбое одного видео)

### Вариант B: Одно видео

```bash
# По URL
python lib/video_processor_assemblyai.py --url "https://youtube.com/watch?v=..."

# Локальный файл
python lib/video_processor_assemblyai.py --file "video.mp4"
```

### Шаг 2: Проверка в PostgreSQL

```sql
-- Проверить добавленные видео
SELECT id, title, category FROM videos ORDER BY id DESC LIMIT 5;

-- Проверить chunks
SELECT COUNT(*) FROM transcripts WHERE video_id = 'VIDEO_ID';

-- Общая статистика
SELECT COUNT(*) as videos FROM videos;
SELECT COUNT(*) as chunks FROM transcripts;
```

### Шаг 3: Добавление в Neo4j граф (только для Варианта B)

При использовании `batch_process_videos.py` Neo4j обновляется автоматически.

Для ручного добавления:
```bash
# Полное переиндексирование (анализирует ВСЕ видео)
python populate_graph.py

# Или только BUILDS_ON связи
python populate_graph.py --builds-on
```

### Шаг 4: Экспорт в Obsidian (опционально)

```bash
# Обновить Obsidian vault после добавления новых видео
python obsidian_export.py --vault "C:/JN/obsidian/jnandez"
```

---

## 2. Работа с Taxonomy

### Файл: `data/poker_taxonomy.yaml`

```yaml
concepts:
  concept_key:
    name: "Human Readable Name"
    aliases:
      - "alias1"
      - "alias2"
      - "русский алиас"
    related:
      - "related concept 1"
      - "related concept 2"
    category: "preflop_action"  # или position, hands, postflop, strategy, etc.
    difficulty: "beginner"      # optional: beginner, intermediate, advanced
```

### Добавление нового концепта

1. Открыть `data/poker_taxonomy.yaml`
2. Добавить концепт в соответствующую секцию
3. Добавить русские и английские алиасы
4. Указать related концепты

### Пример добавления:

```yaml
  facing_steal:
    name: "Facing a Steal"
    aliases:
      - "vs steal"
      - "against steal"
      - "против стила"
      - "защита от стила"
    related:
      - "steal"
      - "defending the bb"
      - "3-bet"
    category: "preflop_action"
```

### После изменения taxonomy:

```bash
# 1. Проверить что taxonomy загружается
python -c "from lib.taxonomy import PokerTaxonomy; t = PokerTaxonomy(); print(len(t.concepts), 'concepts')"

# 2. Добавить новый концепт в Neo4j
python -c "
from lib.graph_db import PokerGraphDB, ConceptNode
db = PokerGraphDB()
db.create_concept(ConceptNode(name='Facing a Steal', category='preflop_action'))
db.concept_relates_to('Facing a Steal', 'Steal')
db.concept_builds_on('Facing a Steal', 'Steal')  # если есть прогрессия
db.close()
"

# 3. Связать с видео (если знаешь какие)
python -c "
from lib.graph_db import PokerGraphDB
db = PokerGraphDB()
db.video_mentions_concept('VIDEO_ID', 'Facing a Steal', 0.7)
db.close()
"
```

---

## 3. Neo4j Knowledge Graph

### Подключение

```python
from lib.graph_db import PokerGraphDB

db = PokerGraphDB()  # использует .env
db.verify_connection()  # проверка
db.get_stats()  # статистика
db.close()
```

### Схема графа

```
(:Video {id, title, url, category})
(:Concept {name, category, difficulty})

(Video)-[:MENTIONS {weight}]->(Concept)
(Concept)-[:RELATES_TO]->(Concept)
(Concept)-[:BUILDS_ON]->(Concept)  # learning progression
```

### Основные операции

```python
# Создать концепт
db.create_concept(ConceptNode(name="...", category="..."))

# Создать видео
db.create_video(VideoNode(id="...", title="...", url="...", category="..."))

# Связи
db.video_mentions_concept(video_id, concept_name, weight)  # 0.0-1.0
db.concept_relates_to(concept1, concept2)
db.concept_builds_on(advanced, basic)  # advanced требует знания basic
```

### Полезные запросы (Cypher)

```cypher
-- Видео о концепте
MATCH (v:Video)-[m:MENTIONS]->(c:Concept {name: "3-Bet"})
RETURN v.title, m.weight ORDER BY m.weight DESC

-- Learning path
MATCH path = (c:Concept {name: "4-Bet"})-[:BUILDS_ON*1..3]->(prereq)
RETURN [n IN nodes(path) | n.name] as path

-- Похожие видео
MATCH (v1:Video {title: "..."})-[:MENTIONS]->(c)<-[:MENTIONS]-(v2:Video)
WHERE v1 <> v2
RETURN v2.title, COUNT(c) as shared ORDER BY shared DESC
```

### Neo4j Aura Console

URL: https://console.neo4j.io

- Визуализация графа
- Выполнение Cypher запросов
- Мониторинг

---

## 4. Полное переиндексирование

Когда нужно: добавили много видео, изменили taxonomy, хотите пересчитать MENTIONS.

```bash
# 1. Очистить граф (опционально)
python -c "
from lib.graph_db import PokerGraphDB
db = PokerGraphDB()
db.clear_all()  # УДАЛИТ ВСЁ!
db.init_schema()
db.close()
"

# 2. Заполнить заново
python populate_graph.py
```

**Важно:** `populate_graph.py` использует LLM для анализа каждого видео (~$0.01-0.02 за видео).

---

## 5. Troubleshooting

### PostgreSQL недоступен из WSL

```bash
# Узнать IP Windows хоста
ip route | grep default | awk '{print $3}'

# Использовать этот IP в DB_CONFIG
```

### Neo4j connection failed

```python
# Проверить credentials в .env
# Проверить что instance запущен в console.neo4j.io
# Free tier может засыпать после неактивности
```

### Taxonomy не находит концепт

```python
# Проверить алиасы
from lib.taxonomy import PokerTaxonomy
t = PokerTaxonomy()
print(t.expand_query("RFI"))  # должен вернуть все алиасы
```

---

## Файлы проекта

| Файл | Назначение |
|------|------------|
| `batch_process_videos.py` | Массовая обработка видео из папки |
| `lib/video_processor_assemblyai.py` | Транскрипция одного видео |
| `lib/graph_db.py` | Neo4j операции |
| `lib/taxonomy.py` | Загрузка и поиск по taxonomy |
| `lib/conversational_rag.py` | RAG + Graph RAG |
| `data/poker_taxonomy.yaml` | Покерные концепты |
| `populate_graph.py` | Заполнение Neo4j из PostgreSQL |
| `chat_with_videos.py` | Интерактивный чат |
| `obsidian_export.py` | Экспорт Neo4j в Obsidian vault |
| `obsidian_import.py` | Импорт изменений из Obsidian в Neo4j |
