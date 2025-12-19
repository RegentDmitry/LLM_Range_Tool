# PyCharm Setup Guide - LLM Range Tool

Step-by-step guide to run the RAG system in PyCharm.

---

## 1. Open Project in PyCharm

1. Launch **PyCharm**
2. **File** → **Open**
3. Navigate to: `C:\GitHub\LLM_Range_Tool`
4. Click **OK**

---

## 2. Setup Python Interpreter

### Option A: Create New Virtual Environment (Recommended)

1. **File** → **Settings** (or `Ctrl+Alt+S`)
2. **Project: LLM_Range_Tool** → **Python Interpreter**
3. Click gear icon ⚙️ → **Add...**
4. Select **Virtualenv Environment**
5. Choose **New environment**
6. Location: `C:\GitHub\LLM_Range_Tool\venv`
7. Base interpreter: Python 3.10+ (or latest)
8. Click **OK**

### Option B: Use Existing Interpreter

1. **File** → **Settings** → **Python Interpreter**
2. Click gear icon ⚙️ → **Add...**
3. Select **System Interpreter**
4. Choose your Python installation
5. Click **OK**

---

## 3. Install Dependencies

### Method 1: Using PyCharm Terminal (Easiest)

1. Open terminal in PyCharm: **View** → **Tool Windows** → **Terminal** (or `Alt+F12`)
2. Run:
   ```bash
   pip install -r requirements.txt
   ```

### Method 2: Using PyCharm UI

1. Open `requirements.txt` file
2. PyCharm will show notification: "Package requirements are not satisfied"
3. Click **Install requirements**
4. Wait for installation to complete

---

## 4. Verify Environment Variables

Check that `.env` file exists and contains your OpenAI key:

1. In PyCharm project tree, find `.env` file
2. Open it
3. Should contain:
   ```
   OPENAI_API_KEY=sk-proj-...your-key...
   ```

**Note:** If you don't see `.env` file:
- Make sure "Show Hidden Files" is enabled
- Or create it manually: **File** → **New** → **File** → name it `.env`

---

## 5. Run Test Script

### Method 1: Right-click run (Easiest)

1. In project tree, find `test_rag.py`
2. **Right-click** on it
3. Select **Run 'test_rag'**
4. Wait for output in Run window

### Method 2: Run Configuration

1. **Run** → **Edit Configurations...**
2. Click **+** (Add New Configuration)
3. Select **Python**
4. Configure:
   - **Name**: `Test RAG System`
   - **Script path**: `C:\GitHub\LLM_Range_Tool\test_rag.py`
   - **Python interpreter**: (should be auto-selected)
   - **Working directory**: `C:\GitHub\LLM_Range_Tool`
5. Click **OK**
6. Click **Run** button (green triangle) or press `Shift+F10`

---

## 6. Expected Output

You should see:

```
============================================================
PLO4/PLO5 GTO Tree Finder - RAG System Test
============================================================

📂 Loading tree data...
✓ Loaded 317 PLO4 trees
✓ Loaded 83 PLO5 trees
✓ Total trees loaded: 400 (317 PLO4 + 83 PLO5)

📊 Database Statistics:
   Total trees: 400
   PLO4: 317 | PLO5: 83
   Cash: 250 | MTT: 150
   ...

🤖 Initializing AI agent...
✓ Agent ready

============================================================
Running Test Queries
============================================================

[Query 1] Find trees for 6-max cash PLO4 at 100bb
------------------------------------------------------------
✓ Found 3 matching tree(s):

1. PLO - 100bb - 6p
   Category: PLO
   ...
```

Then it will enter **Interactive Mode** where you can type your own questions.

---

## 7. Run Simple Example

For a quicker test without interactive mode:

1. Right-click `example_simple.py`
2. Select **Run 'example_simple'**

This runs one query and exits.

---

## 8. Debugging (Optional)

To debug the code:

1. Set breakpoints: Click in left margin next to line numbers
2. Right-click on `test_rag.py` or `example_simple.py`
3. Select **Debug 'test_rag'** (or press `Shift+F9`)
4. Use debugger controls to step through code

---

## 9. Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'dotenv'"

**Solution:**
```bash
pip install python-dotenv
```

### Issue 2: "ModuleNotFoundError: No module named 'pydantic_ai'"

**Solution:**
```bash
pip install pydantic-ai
```

### Issue 3: "OpenAI API key not found"

**Solution:**
1. Check `.env` file exists in project root
2. Check it contains: `OPENAI_API_KEY=sk-...`
3. Restart PyCharm to reload environment variables

### Issue 4: "FileNotFoundError: temp/preflop-tree-dev.json"

**Solution:**
- Make sure `temp/` folder exists with JSON files
- Check working directory is set to project root

### Issue 5: "Invalid API key"

**Solution:**
- Verify your OpenAI key at https://platform.openai.com/api-keys
- Check for extra spaces in `.env` file
- Make sure key is valid and has credits

---

## 10. PyCharm Tips

### View File Structure
- **Alt+7** - Open Structure window
- Shows all classes and functions

### Quick Navigation
- **Ctrl+Click** on function/class - Go to definition
- **Ctrl+B** - Go to declaration
- **Alt+Left/Right** - Navigate back/forward

### Search Everything
- **Shift+Shift** - Search Anywhere
- Type filename, class name, or function name

### Terminal Shortcuts
- **Alt+F12** - Open/close terminal
- **Ctrl+Shift+T** - New terminal tab

### Run/Debug Shortcuts
- **Shift+F10** - Run current file
- **Shift+F9** - Debug current file
- **Ctrl+F5** - Rerun

---

## 11. Project Structure in PyCharm

```
LLM_Range_Tool/
├── .env                    ← Your API keys (hidden by default)
├── .gitignore
├── requirements.txt        ← Dependencies
├── README.md
├── PYCHARM_GUIDE.md       ← This file
│
├── config/
│   └── credentialsprivate.py  ← AWS credentials
│
├── lib/                   ← Core libraries
│   ├── data_loader.py     ← Load trees from JSON
│   ├── query_agent.py     ← AI agent for parsing
│   └── boto3_utils.py     ← AWS utilities
│
├── models/                ← Pydantic models
│   └── preflop_models.py
│
├── temp/                  ← Local data (not in git)
│   ├── preflop-tree-dev.json
│   └── 5card-preflop-tree-dev.json
│
├── test_rag.py           ← 🎯 Interactive test (RUN THIS)
└── example_simple.py     ← Simple example
```

---

## 12. Next Steps

After successful run:

1. **Try your own queries** in interactive mode:
   - "Find trees for heads-up MTT"
   - "ICM situation 6-max"
   - "найди дерево для кэш игры" (Russian works!)

2. **Modify the code**:
   - Change model in `lib/query_agent.py`
   - Add custom filters
   - Format output differently

3. **Integrate into your app**:
   - Import modules: `from lib import TreeDataLoader, TreeQueryAgent`
   - Use in your own scripts

---

## Support

If something doesn't work:
1. Check Python version: `python --version` (should be 3.10+)
2. Check dependencies: `pip list | grep pydantic`
3. Check OpenAI key: verify at https://platform.openai.com/api-keys
4. Check working directory: should be `C:\GitHub\LLM_Range_Tool`

---

**Ready to go!** Run `test_rag.py` and start asking questions about GTO trees! 🚀
