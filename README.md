# LLM Range Tool - RAG System for PLO4/PLO5 GTO Solutions

Prototype RAG (Retrieval-Augmented Generation) system for working with a database of GTO solutions for Omaha (PLO4/PLO5).

**Natural language queries → Structured search → GTO trees with S3 links**

## Description

Ask questions in natural language and get relevant GTO decision trees:
- "Find trees for 6-max cash PLO4 at 100bb"
- "heads up MTT with ante"
- "ICM situation 6-max"
- "найди дерево для 6-макс кэш на стеках 100бб" (Russian supported!)

**Database:**
- 317 trees for PLO4
- 83 trees for PLO5
- Coverage: Cash, MTT, ICM, Exploitative strategies
- Various formats: Heads-Up, 6-Max, with ante, straddle, etc.

## How It Works

```
User Question → Pydantic AI Agent (GPT-4) → Structured Query → Filter Trees → Results with S3 Links
```

No vector database needed - uses intelligent query parsing + filtering for fast, accurate results.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup OpenAI API Key

```bash
# Copy template
cp .env.example .env

# Edit .env and add your OpenAI key
OPENAI_API_KEY=sk-your-key-here
```

Or export directly:
```bash
export OPENAI_API_KEY='sk-your-key-here'
```

### 3. Run Automated Tests

```bash
python run_rag_tests.py
```

This will:
- Load 400 trees from local JSON
- Show database statistics
- Run 5 predefined test queries
- Verify everything works

### 4. Run Interactive Mode

```bash
python run_rag_manual.py
```

Ask your own questions in natural language!

### 5. Run Simple Example

```bash
python example_simple.py
```

Minimal example (one query and exit)

## Usage Example

```python
import asyncio
from lib import TreeDataLoader, TreeQueryAgent

async def main():
    # Load data (once at startup)
    loader = TreeDataLoader()
    trees = loader.load_all_trees()

    # Create AI agent
    agent = TreeQueryAgent(model='openai:gpt-4o-mini')

    # Ask a question
    results = await agent.search_trees(
        "Find trees for 6-max cash PLO4 at 100bb",
        trees
    )

    # Show results
    print(agent.format_results(results))

asyncio.run(main())
```

## Project Structure

```
├── config/                           # AWS configuration
│   ├── credentialsprivate.default.py # Credentials template
│   └── credentialsprivate.py         # ⚠️  Your AWS credentials (not committed!)
├── lib/                              # Core libraries
│   ├── boto3_utils.py                # S3 and DynamoDB utilities
│   ├── data_loader.py                # Load trees from JSON/DynamoDB
│   └── query_agent.py                # Pydantic AI agent for query parsing
├── models/                           # Pydantic models
│   └── preflop_models.py             # Models for RAG system
├── temp/                             # Local data (not committed)
│   ├── preflop-tree-dev.json         # PLO4 trees (317)
│   ├── 5card-preflop-tree-dev.json   # PLO5 trees (83)
│   └── tree-tags-dev.json            # Tags reference
├── run_rag_tests.py                  # 🎯 Automated tests (5 test queries)
├── run_rag_manual.py                 # 💬 Interactive mode (ask your own questions)
├── example_simple.py                 # Simple usage example
└── requirements.txt                  # Python dependencies
```

## Supported LLM Models

Configure in `TreeQueryAgent`:

```python
# OpenAI (default - fast and cheap)
agent = TreeQueryAgent(model='openai:gpt-4o-mini')

# OpenAI GPT-4 (more accurate)
agent = TreeQueryAgent(model='openai:gpt-4o')

# Anthropic Claude (optional)
agent = TreeQueryAgent(model='anthropic:claude-3-5-sonnet-20241022')
```

## Example Queries

**English:**
- "Find trees for 6-max cash PLO4 at 100bb"
- "heads up MTT"
- "ICM situation"
- "exploitative trees"
- "6-max with ante"

**Russian:**
- "найди дерево для 6-макс кэш на стеках 100бб"
- "хуху с анте"
- "турнирная ситуация ICM"

The AI agent understands natural language variations!

## AWS Resources (Optional)

For direct AWS access (not needed for local testing):

### DynamoDB Tables:
- `preflop-tree-dev` - PLO4 trees
- `5card-preflop-tree-dev` - PLO5 trees
- `tree-tags-dev` - tags reference

### S3 Buckets:

**Trees (JSON):**
- PLO4: `preflop-trees`
- PLO5: `plo5-preflop-trees`

**Preflop Ranges:**
- PLO4: `postflop-ranges-json`
- PLO5: `plo5-preflop-ranges`

### Setup AWS Credentials

Only needed for direct AWS access:

```bash
cp config/credentialsprivate.default.py config/credentialsprivate.py
# Edit and add your AWS keys
```

## Documentation

- [Models Documentation](README_PREFLOP_MODELS.md) - Detailed Pydantic models reference
- [PyCharm Guide](PYCHARM_GUIDE.md) - Setup guide for PyCharm IDE
- [Quick Start](QUICKSTART.md) - Quick start guide
- [Project Architecture](PROJECT_ARCHITECTURE.md) - Future web service architecture

## Development

### Running Tests

```bash
# Automated tests (5 predefined queries)
python run_rag_tests.py

# Interactive mode (ask your own questions)
python run_rag_manual.py

# Simple example (one query)
python example_simple.py
```

### Using in PyCharm

**See detailed guide:** [PYCHARM_GUIDE.md](PYCHARM_GUIDE.md)

Quick steps:
1. Open project in PyCharm
2. Install dependencies: `pip install -r requirements.txt`
3. `.env` file should already contain your OpenAI key
4. Right-click `run_rag_tests.py` → **Run** (for automated tests)
5. Or `run_rag_manual.py` → **Run** (for interactive mode)

## Security

⚠️ **IMPORTANT:** Never commit these files to git:
- `config/credentialsprivate.py` (AWS credentials)
- `.env` (API keys)
- `temp/` (local data)

All are already in `.gitignore`. Always check before committing:

```bash
git status --ignored
```

## License

Private project
