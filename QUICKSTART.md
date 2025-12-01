# Quick Start - 3 Steps to Run

## 1️⃣ Install Dependencies

Open PyCharm Terminal (`Alt+F12`) and run:

```bash
pip install -r requirements.txt
```

Wait ~30 seconds for installation.

---

## 2️⃣ Check API Key

Your OpenAI key is already in `.env` file:

```
OPENAI_API_KEY=sk-proj-...
```

✅ You're good to go!

---

## 3️⃣ Run

**Option A: Interactive Mode**

Right-click `test_rag.py` → **Run 'test_rag'**

- Shows statistics
- Runs test queries
- Lets you ask your own questions

**Option B: Simple Example**

Right-click `example_simple.py` → **Run 'example_simple'**

- One query
- Quick test
- Shows output format

---

## That's It!

You should see output like:

```
📂 Loading tree data...
✓ Loaded 317 PLO4 trees
✓ Loaded 83 PLO5 trees

🤖 Initializing AI agent...
✓ Agent ready

[Query 1] Find trees for 6-max cash PLO4 at 100bb
------------------------------------------------------------
✓ Found 3 matching tree(s):

1. PLO - 100bb - 6p
   ...
```

---

## Need Help?

- **Full PyCharm guide:** [PYCHARM_GUIDE.md](PYCHARM_GUIDE.md)
- **Project docs:** [README.md](README.md)
- **Models reference:** [README_PREFLOP_MODELS.md](README_PREFLOP_MODELS.md)

---

## Quick Tips

### Change LLM Model

Edit `test_rag.py` or `example_simple.py`:

```python
# Fast & cheap (default)
agent = TreeQueryAgent(model='openai:gpt-4o-mini')

# Better quality
agent = TreeQueryAgent(model='openai:gpt-4o')
```

### Ask Questions

In interactive mode, try:
- "Find trees for 6-max cash PLO4 at 100bb"
- "heads up MTT with ante"
- "ICM situation"
- "найди дерево для кэш игры" (Russian!)

### Debug

Right-click script → **Debug** (instead of Run)

Set breakpoints by clicking line numbers.

---

**Happy coding! 🚀**
