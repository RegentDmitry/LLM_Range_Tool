# Pydantic Models for PLO4/PLO5 Preflop RAG System

## Overview

Pydantic models for building a RAG (Retrieval-Augmented Generation) system on PLO4 and PLO5 preflop data.

## Key Models

### `PreflopTree`

Core model containing essential parameters for identifying and searching preflop situations.

**Key Identification Parameters:**
- `tree_key` - unique tree identifier (e.g., "PLO500_100_6")
- `profile` - game profile (primary identifier, e.g., "PLO500")
- `category` - tree category (e.g., "PLO", "MTT", "PLO-EXP")
- `number_of_players` - number of players (2-8)
- `stack_size` - stack size in BB
- `game_type` - game type (PLO4/PLO5)

**Computed Properties:**
- `display_name` - human-readable name
- `game_format` - game format (Cash/MTT)
- `is_icm` - whether tree uses ICM
- `is_exploitative` - whether tree is exploitative

**Methods:**
- `to_search_document()` - converts tree to text for semantic search
- `get_s3_tree_path()` - generates S3 path to JSON tree
- `get_s3_ranges_prefix()` - generates S3 prefix for ranges folder

### `PreflopTags`

Tags for describing preflop situations, used for semantic search and filtering.

### `PreflopQuery`

Query model for searching preflop situations with multiple filters:
- Basic: `game_type`, `game_format`, `number_of_players`, `stack_size`
- Advanced: `category`, `profile`, `poker_room`, `stake`
- Special: `with_ante`, `with_straddle`, `icm_only`, `exploitative_only`
- Free text: `query_text`
- Settings: `max_results` (default: 10)

### `PreflopSearchResult`

Search result containing:
- `tree` - found tree
- `relevance_score` - relevance (0-1)
- `s3_tree_path` - path to JSON tree in S3
- `s3_ranges_prefix` - prefix for ranges folder in S3

## Usage Example

```python
from models.preflop_models import (
    PreflopTree,
    PreflopQuery,
    GameType,
    GameFormat,
    parse_tree_from_dynamodb,
    filter_trees_by_query,
)
import json

# Load data from DynamoDB
with open('temp/preflop-tree-dev.json', 'r') as f:
    data = json.load(f)

# Parse trees
trees = [parse_tree_from_dynamodb(item) for item in data]

# Create query
query = PreflopQuery(
    game_type=GameType.PLO4,
    game_format=GameFormat.CASH,
    number_of_players=6,
    stack_size=100,
    max_results=10
)

# Filter trees
results = filter_trees_by_query(trees, query)

# Use results
for tree in results:
    print(f"Tree: {tree.display_name}")
    print(f"  S3 Tree: {tree.get_s3_tree_path()}")
    print(f"  S3 Ranges: {tree.get_s3_ranges_prefix()}")
```

## Generating Search Documents for RAG

```python
# Generate documents for indexing in vector database
search_documents = []

for tree in trees:
    if tree.is_active:
        doc = tree.to_search_document()
        search_documents.append({
            'id': tree.tree_key,
            'text': doc,
            'metadata': {
                'category': tree.category,
                'players': tree.number_of_players,
                'stack': tree.stack_size,
                'game_type': tree.game_type,
            }
        })

# Now index search_documents in ChromaDB, Pinecone, etc.
```

## Query Examples

```python
# 6-max Cash 100bb trees
query = PreflopQuery(
    game_type=GameType.PLO4,
    game_format=GameFormat.CASH,
    number_of_players=6,
    stack_size=100
)

# MTT trees
query = PreflopQuery(game_format=GameFormat.MTT)

# Heads-Up trees
query = PreflopQuery(number_of_players=2)

# Trees with ante
query = PreflopQuery(with_ante=True)

# ICM trees
query = PreflopQuery(icm_only=True)

# Exploitative trees
query = PreflopQuery(exploitative_only=True)

# Free text query
query = PreflopQuery(query_text="GGPoker 100bb 6-max with ante")
```

## S3 Path Structure

### Tree JSON Files

**Buckets:**
- PLO4: `preflop-trees`
- PLO5: `plo5-preflop-trees`

**Path Format:** `{category}/{tree_key}.json.gz`
- PLO4 Example: `PLO/PLO500_30_6.json.gz`
- PLO5 Example: `PLO5-COIN/PLO5C-100CHU_50_2.json.gz`

**Full URLs:**
- PLO4: `https://preflop-trees.s3.dualstack.eu-central-1.amazonaws.com/{category}/{tree_key}.json.gz`
- PLO5: `https://plo5-preflop-trees.s3.dualstack.eu-central-1.amazonaws.com/{category}/{tree_key}.json.gz`

### Preflop Ranges

**Buckets:**
- PLO4: `postflop-ranges-json`
- PLO5: `plo5-preflop-ranges`

**Path Format:** `{category}/{profile}/{stack_size}/{players}/preflop/`
- PLO4 Example: `PLO/PLO500/100/6/preflop/`
- PLO5 Example: `PLO5-COIN/PLO5C-1000CHU/100/2/preflop/`

**Full URLs:**
- PLO4: `https://postflop-ranges-json.s3.dualstack.eu-central-1.amazonaws.com/{category}/{profile}/{stack_size}/{players}/preflop/`
- PLO5: `https://plo5-preflop-ranges.s3.dualstack.eu-central-1.amazonaws.com/{category}/{profile}/{stack_size}/{players}/preflop/`

### Code Examples

```python
tree = trees[0]  # PLO4 tree with profile="PLO500", stack_size=100, players=6

# Tree JSON
tree.get_s3_bucket()          # "preflop-trees"
tree.get_s3_tree_path()       # "PLO/PLO500_100_6.json.gz"
tree.get_s3_tree_url()        # "https://preflop-trees.s3.dualstack.eu-central-1.amazonaws.com/PLO/PLO500_100_6.json.gz"

# Ranges
tree.get_s3_ranges_bucket()   # "postflop-ranges-json"
tree.get_s3_ranges_prefix()   # "PLO/PLO500/100/6/preflop/"
tree.get_s3_ranges_url()      # "https://postflop-ranges-json.s3.dualstack.eu-central-1.amazonaws.com/PLO/PLO500/100/6/preflop/"
```

## Data Statistics

From preflop-tree-dev table analysis:

- **Total trees**: 317
- **Active**: 301 (95%)
- **ICM trees**: 50 (15.8%)
- **Exploitative trees**: 51 (16.1%)
- **With ante**: 119 (37.5%)
- **With straddle**: 17 (5.4%)

**By Player Count:**
- Heads-Up (2p): 53 (16.7%)
- 4-Max: 62 (19.6%)
- 6-Max: 164 (51.7%)
- 8-Max: 18 (5.7%)

**By Stack Size:**
- 0-20bb: 26 (8.2%)
- 20-50bb: 62 (19.6%)
- 50-100bb: 53 (16.7%)
- 100-200bb: 147 (46.4%)
- 200+bb: 29 (9.1%)

## PLO5 Support

Models support PLO5 through `game_type` parameter. PLO5 uses different S3 buckets:

```python
tree = PreflopTree(
    tree_key="PLO5C-1000CHU_100_2",
    profile="PLO5C-1000CHU",
    category="PLO5-COIN",
    number_of_players=2,
    stack_size=100,
    game_type=GameType.PLO5
)

# Tree JSON - uses plo5-preflop-trees bucket
tree.get_s3_bucket()     # "plo5-preflop-trees"
tree.get_s3_tree_path()  # "PLO5-COIN/PLO5C-1000CHU_100_2.json.gz"
tree.get_s3_tree_url()   # "https://plo5-preflop-trees.s3.dualstack.eu-central-1.amazonaws.com/PLO5-COIN/PLO5C-1000CHU_100_2.json.gz"

# Ranges - uses plo5-preflop-ranges bucket
tree.get_s3_ranges_bucket()  # "plo5-preflop-ranges"
tree.get_s3_ranges_prefix()  # "PLO5-COIN/PLO5C-1000CHU/100/2/preflop/"
tree.get_s3_ranges_url()     # "https://plo5-preflop-ranges.s3.dualstack.eu-central-1.amazonaws.com/PLO5-COIN/PLO5C-1000CHU/100/2/preflop/"
```

## Testing

Run tests:

```bash
python3 test_preflop_models.py
```

Tests cover:
1. Parsing trees from DynamoDB format
2. Computed properties
3. Search document generation
4. Various query types
5. Search result creation
6. Data statistics

## Files

- `models/preflop_models.py` - core models
- `models/__init__.py` - model exports
- `test_preflop_models.py` - test script
- `temp/preflop-tree-dev.json` - exported preflop data
- `temp/tree-tags-dev.json` - exported tag data

## Pydantic AI Integration

Models are ready for use with Pydantic AI for building RAG system:

```python
from pydantic_ai import Agent
from models.preflop_models import PreflopTree, PreflopQuery

agent = Agent(
    'openai:gpt-4',
    result_type=PreflopTree,
    system_prompt='''
    You are a PLO4/PLO5 preflop strategy assistant.
    Help players find the right decision tree for their situation.
    '''
)

result = await agent.run(
    "Find me a tree for 6-max cash game at 100bb in PLO4"
)
```

## Requirements

- pydantic >= 2.0

## Notes

1. Models use `use_enum_values = True`, so enum values are automatically converted to strings.

2. All aliases (e.g., `treeKey` -> `tree_key`) are handled automatically via `populate_by_name = True`.

3. Technical parameters (treeOrder, profileOrder, raiseSizeMapping, lockedNodes, isActive) are intentionally excluded from queries as they're not needed for situation identification. All trees in the database are considered active and available.
