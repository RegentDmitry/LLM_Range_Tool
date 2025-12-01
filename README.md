# LLM Range Tool - RAG System for PLO4/PLO5 GTO Solutions

Prototype RAG (Retrieval-Augmented Generation) system for working with a database of GTO solutions for Omaha (PLO4/PLO5).

## Description

The system allows finding suitable GTO decision trees in the database based on text queries. The database contains:
- 317 trees for PLO4
- 83 trees for PLO5
- Coverage: Cash, MTT, ICM, Exploitative strategies
- Various formats: Heads-Up, 6-Max, with ante, straddle, etc.

## Project Structure

```
├── config/                           # AWS configuration
│   ├── credentialsprivate.default.py # Credentials template
│   └── credentialsprivate.py         # ⚠️  Your AWS credentials (not committed!)
├── lib/                              # Data access libraries
│   └── boto3_utils.py                # S3 and DynamoDB utilities
├── models/                           # Pydantic models
│   └── preflop_models.py             # Models for RAG system
├── temp/                             # Local data (not committed)
│   ├── preflop-tree-dev.json         # PLO4 trees (317)
│   ├── 5card-preflop-tree-dev.json   # PLO5 trees (83)
│   └── tree-tags-dev.json            # Tags reference
├── main.py                           # Main script
└── README_PREFLOP_MODELS.md          # Models documentation
```

## Quick Start

### 1. Setup Credentials

Copy the template and fill in your AWS credentials:

```bash
cp config/credentialsprivate.default.py config/credentialsprivate.py
```

Edit `config/credentialsprivate.py`:

```python
AwsAccessKey = 'your-aws-access-key'
AwsSecret = 'your-aws-secret'
AwsRegion = 'eu-central-1'
```

### 2. Install Dependencies

```bash
pip install boto3 pydantic pydantic-ai
```

### 3. Usage

```python
from models import PreflopTree, PreflopQuery, parse_tree_from_dynamodb
from lib import get_dynamodb_record
import json

# Working with local data
with open('temp/preflop-tree-dev.json', 'r') as f:
    trees_data = json.load(f)

trees = [parse_tree_from_dynamodb(item) for item in trees_data]

# Search example
query = PreflopQuery(
    game_type="plo4",
    number_of_players=6,
    stack_size=100,
    max_results=10
)

# Your RAG logic here...
```

## AWS Resources

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

## Documentation

Detailed models documentation: [README_PREFLOP_MODELS.md](README_PREFLOP_MODELS.md)

## Security

⚠️ **IMPORTANT:** Never commit the `config/credentialsprivate.py` file to git!

The file is already added to `.gitignore`, but always check before committing:

```bash
git status --ignored
```

## Development

For local development without AWS, you can use JSON files from the `temp/` folder.

## License

Private project
