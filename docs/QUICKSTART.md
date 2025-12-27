# RangeLab AI - Quick Start

Быстрый старт для продолжения работы над проектом.

## Запуск чата

```bash
cd /mnt/c/GitHub/LLM_Range_Tool
venv/bin/python chat_with_videos.py
```

## Проверка состояния

### PostgreSQL
```bash
venv/bin/python -c "
import psycopg2
conn = psycopg2.connect(host='172.24.192.1', port=5432, database='rangelab', user='postgres', password='dbpass')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM videos')
print(f'Videos: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM transcripts')
print(f'Transcripts: {cur.fetchone()[0]}')
conn.close()
"
```

### Neo4j
```bash
venv/bin/python -c "
from lib.graph_db import PokerGraphDB
db = PokerGraphDB()
print('Connected:', db.verify_connection())
print('Stats:', db.get_stats())
db.close()
" 2>&1 | grep -v notification
```

### Taxonomy
```bash
venv/bin/python -c "
from lib.taxonomy import PokerTaxonomy
t = PokerTaxonomy()
print(f'Concepts: {len(t.concepts)}')
print(f'Example expansion: RFI ->', t.expand_query('RFI'))
"
```

## Типичные задачи

### Добавить новое видео

```bash
# 1. Транскрибировать
venv/bin/python lib/video_processor_assemblyai.py --url "https://youtube.com/watch?v=..."

# 2. Добавить в граф (перезапустит анализ всех видео!)
venv/bin/python populate_graph.py
```

### Добавить концепт в taxonomy

1. Редактировать `data/poker_taxonomy.yaml`
2. Добавить в Neo4j:

```bash
venv/bin/python -c "
from lib.graph_db import PokerGraphDB, ConceptNode
db = PokerGraphDB()
db.create_concept(ConceptNode(name='New Concept', category='preflop_action'))
db.concept_relates_to('New Concept', 'Related Concept')
db.close()
"
```

### Связать видео с концептом

```bash
venv/bin/python -c "
from lib.graph_db import PokerGraphDB
db = PokerGraphDB()
db.video_mentions_concept('VIDEO_ID', 'Concept Name', 0.7)  # weight 0-1
db.close()
"
```

### Добавить learning progression

```bash
venv/bin/python -c "
from lib.graph_db import PokerGraphDB
db = PokerGraphDB()
db.concept_builds_on('Advanced Concept', 'Basic Concept')
db.close()
"
```

## Файлы для редактирования

| Файл | Когда менять |
|------|--------------|
| `data/poker_taxonomy.yaml` | Добавление концептов/синонимов |
| `lib/conversational_rag.py` | Изменение логики поиска/промптов |
| `lib/graph_db.py` | Новые graph queries |
| `populate_graph.py` | Изменение логики индексации |
| `chat_with_videos.py` | UI чата |

## Полезные команды

```bash
# Посмотреть все видео
venv/bin/python -c "
import psycopg2
conn = psycopg2.connect(host='172.24.192.1', port=5432, database='rangelab', user='postgres', password='dbpass')
cur = conn.cursor()
cur.execute('SELECT title, category FROM videos ORDER BY title')
for row in cur.fetchall(): print(f'{row[1]}: {row[0]}')
conn.close()
"

# Посмотреть все концепты в Neo4j
venv/bin/python -c "
from lib.graph_db import PokerGraphDB
db = PokerGraphDB()
for c in db.get_all_concepts(): print(c['name'])
db.close()
" 2>&1 | grep -v notification

# Тест taxonomy expansion
venv/bin/python -c "
from lib.taxonomy import PokerTaxonomy
t = PokerTaxonomy()
print(t.expand_query('стил'))
"
```

## Ссылки

- Neo4j Console: https://console.neo4j.io
- OpenAI API: https://platform.openai.com
- AssemblyAI: https://www.assemblyai.com

## Текущее состояние (Dec 2024)

- 71 видео (PLO4 + PLO5)
- 1497 transcript chunks с embeddings
- 90 концептов в taxonomy
- 687 MENTIONS связей в графе
- Graph RAG интегрирован
