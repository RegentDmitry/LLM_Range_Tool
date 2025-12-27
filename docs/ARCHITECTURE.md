# RangeLab AI - Architecture

## Overview

Система для поиска и навигации по покерным обучающим видео с использованием:
- **Semantic Search** (PostgreSQL + pgvector)
- **Taxonomy Expansion** (синонимы и алиасы)
- **Knowledge Graph** (Neo4j - связи между концептами)

## Stack

```
┌────────────────────────────────────────────────────────────────┐
│                        Frontend                                 │
│                   chat_with_videos.py                          │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                  ConversationalVideoRAG                         │
│                 lib/conversational_rag.py                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Pydantic AI  │  │  OpenAI      │  │  Translation         │  │
│  │ Agent        │  │  GPT-4o      │  │  (auto ru→en)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   PostgreSQL    │  │   Taxonomy      │  │   Neo4j Aura        │
│   + pgvector    │  │   YAML          │  │   Knowledge Graph   │
│                 │  │                 │  │                     │
│ • videos        │  │ • 90 concepts   │  │ • 71 Video nodes    │
│ • transcripts   │  │ • 400+ aliases  │  │ • 90 Concept nodes  │
│ • embeddings    │  │ • related       │  │ • 687 MENTIONS      │
│                 │  │                 │  │ • 107 RELATES_TO    │
│                 │  │                 │  │ • 35 BUILDS_ON      │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
```

## Agent Tools

ConversationalVideoRAG предоставляет агенту следующие tools:

### Semantic Search
| Tool | Описание |
|------|----------|
| `search_videos` | Поиск по embeddings + taxonomy boost |
| `get_conversation_context` | История диалога |

### Graph Search (Neo4j)
| Tool | Описание |
|------|----------|
| `find_learning_path` | Что изучить перед X? (BUILDS_ON) |
| `find_related_videos` | Похожие видео (через shared concepts) |
| `find_videos_by_concepts` | Видео на пересечении концептов |
| `get_concept_videos` | Все видео о концепте |

## Data Flow

### 1. Индексация видео

```
YouTube URL
    │
    ▼
AssemblyAI (транскрипция)
    │
    ▼
PostgreSQL
├── videos (id, title, url, category)
└── transcripts (video_id, text, timestamp, embedding)
    │
    ▼
OpenAI Embeddings (text-embedding-3-small)
```

### 2. Построение графа

```
poker_taxonomy.yaml
    │
    ├──▶ Concept nodes (Neo4j)
    └──▶ RELATES_TO edges

PostgreSQL videos
    │
    ├──▶ Video nodes (Neo4j)
    │
    ▼
LLM Analysis (GPT-4o-mini)
    │
    └──▶ MENTIONS edges (video → concept, weight)

Manual/Config
    │
    └──▶ BUILDS_ON edges (learning progression)
```

### 3. Поиск (runtime)

```
User Query (любой язык)
    │
    ▼
Translation (если не английский)
    │
    ▼
Taxonomy Expansion ("RFI" → ["RFI", "raise first in", "open raise"...])
    │
    ├──▶ Semantic Search (pgvector cosine similarity)
    │         + title match boost (+0.3)
    │
    └──▶ Graph Search (если нужен)
              │
              ├── Learning path (BUILDS_ON traversal)
              ├── Related videos (shared concepts)
              └── Multi-concept (intersection)
    │
    ▼
LLM Synthesis (GPT-4o)
    │
    ▼
Structured Response (answer, sources, confidence)
```

## Databases

### PostgreSQL Schema

```sql
CREATE TABLE videos (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    url VARCHAR,
    category VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE transcripts (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR REFERENCES videos(id),
    text TEXT NOT NULL,
    timestamp VARCHAR,
    embedding vector(1536)  -- OpenAI text-embedding-3-small
);

CREATE INDEX ON transcripts USING ivfflat (embedding vector_cosine_ops);
```

### Neo4j Schema

```cypher
// Nodes
(:Video {id: string, title: string, url: string, category: string})
(:Concept {name: string, category: string, difficulty: string?})

// Relationships
(Video)-[:MENTIONS {weight: float}]->(Concept)
(Concept)-[:RELATES_TO]->(Concept)
(Concept)-[:BUILDS_ON]->(Concept)

// Constraints
CREATE CONSTRAINT video_id FOR (v:Video) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT concept_name FOR (c:Concept) REQUIRE c.name IS UNIQUE;
```

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# For transcription
ASSEMBLYAI_API_KEY=...

# For knowledge graph
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...

# Optional
POSTGRES_HOST=172.24.192.1  # auto-detected in WSL
```

## Graceful Degradation

Система работает даже если часть компонентов недоступна:

| Компонент | Если недоступен |
|-----------|-----------------|
| Neo4j | Graph tools отключаются, semantic search работает |
| Taxonomy | Только exact match, без expansion |
| OpenAI | Система не работает (критично) |
| PostgreSQL | Система не работает (критично) |

## Performance

| Операция | Время |
|----------|-------|
| Semantic search | ~200ms |
| Graph query | ~100ms |
| LLM response | ~2-5s |
| Full chat turn | ~3-7s |

## Costs (OpenAI)

| Операция | Стоимость |
|----------|-----------|
| Embedding (1 chunk) | ~$0.00002 |
| Chat (GPT-4o) | ~$0.01-0.03 per query |
| Graph population (1 video) | ~$0.01-0.02 |
