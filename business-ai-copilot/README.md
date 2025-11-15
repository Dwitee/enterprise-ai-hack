# Business SQL Insights Copilot (Gemini + MSSQL)

This app lets you ask **natural language questions** about the
`WideWorldImporters_Base` SQL Server database and returns:

- A clear **insightful explanation** (via Gemini)
- The **generated T-SQL query**
- A **data table** of results
- A quick **chart** for numeric data

## Setup

```bash
cd business-ai-copilot
python -m venv .venv
source .venv/bin/activate  # on macOS / Linux
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env       # then edit .env with real password + Gemini key
```

Run a quick DB test:

```bash
python -c "from db.database import run_query; print(run_query('SELECT 1 AS ok;'))"
```

Run a quick Gemini test:

```bash
python -c "from ai.llm import llm; print(llm('Reply with the single word OK'))"
```

Then start the app:

```bash
streamlit run app.py
```
