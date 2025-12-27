# RangeLab AI - Roadmap

## Completed

### Level 1: Vector Search
- [x] PostgreSQL + pgvector
- [x] OpenAI embeddings (text-embedding-3-small)
- [x] AssemblyAI transcription
- [x] 71 videos indexed

### Level 2: Taxonomy
- [x] poker_taxonomy.yaml (90 концептов)
- [x] Query expansion (RFI → "raise first in", etc.)
- [x] Русские алиасы

### Level 3: Hybrid Search
- [x] Semantic + taxonomy title matching
- [x] +30% boost для title match

### Level 4: Knowledge Graph
- [x] Neo4j Aura (cloud)
- [x] Video и Concept nodes
- [x] MENTIONS, RELATES_TO, BUILDS_ON edges
- [x] Learning path queries

### Level 5: Graph RAG
- [x] Интеграция Neo4j в ConversationalVideoRAG
- [x] Graph tools для агента
- [x] Graceful degradation

---

## Potential Improvements

### Search Quality
- [ ] Re-ranking с cross-encoder
- [ ] Chunk overlap для лучшего контекста
- [ ] Query понимание (intent detection)

### Knowledge Graph
- [ ] Автоматическое извлечение концептов из новых видео
- [ ] Weights decay (старые видео менее релевантны?)
- [ ] Больше BUILDS_ON связей

### Taxonomy
- [ ] Hierarchy (категории → подкатегории)
- [ ] Difficulty levels для concepts
- [ ] Auto-suggest новых концептов из транскриптов

### UX
- [ ] Web UI (Streamlit/Gradio)
- [ ] Timestamps как кликабельные ссылки
- [ ] "Watch next" рекомендации после ответа

### Performance
- [ ] Caching embeddings
- [ ] Batch processing для новых видео
- [ ] Streaming responses

### Content
- [ ] Больше видео (100+)
- [ ] Разные авторы/источники
- [ ] Hand history analysis integration

---

## Technical Debt

- [ ] Tests для graph_db.py
- [ ] Tests для conversational_rag.py
- [ ] CI/CD pipeline
- [ ] Docker compose для локальной разработки
- [ ] Миграции для PostgreSQL schema

---

## Notes for Future Development

### Добавление нового источника видео

1. Создать новый processor в `lib/`
2. Следовать интерфейсу VideoProcessorAssemblyAI
3. Обновить `populate_graph.py` если нужна другая логика

### Изменение LLM

1. Pydantic AI поддерживает разные модели
2. Изменить в `ConversationalVideoRAG.__init__`
3. Для Anthropic Claude: `from pydantic_ai.models.anthropic import AnthropicModel`

### Railway Deployment

1. PostgreSQL: использовать Railway PostgreSQL addon
2. Neo4j: оставить Neo4j Aura (уже cloud)
3. Environment variables: настроить в Railway dashboard

### Если Neo4j Aura Free Tier закончится

Альтернативы:
- Neo4j AuraDB Professional ($65/mo)
- Self-hosted Neo4j на Railway
- Переход на Apache AGE (PostgreSQL extension) - меньше функций
