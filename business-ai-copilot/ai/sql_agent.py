from typing import Any, Dict, List
from ai.llm import llm
from db.database import run_query, get_schema_summary

# Capture a textual summary of the live DB schema to guide SQL generation
SCHEMA_SUMMARY = get_schema_summary()


def _clean_sql_output(raw: str) -> str:
    """Clean up the LLM output to extract a usable SQL string."""
    if not raw:
        return ""
    sql = raw.strip()
    # Remove common markdown code fences if the model added them
    sql = sql.replace("```sql", "").replace("```", "").strip()
    lines = sql.splitlines()
    # Sometimes the first line is just "sql"
    if lines and lines[0].strip().lower() == "sql":
        sql = "\n".join(lines[1:]).strip()
    return sql


def answer_from_sql(question: str) -> Dict[str, Any]:
    """
    Use Gemini to write a SELECT query, execute it, then explain.

    Returns dict with:
    - answer: natural language explanation
    - rows: list of dicts (query result)
    - sql: generated SQL string
    """

    sql_prompt = f"""
You are a senior analytics engineer generating T-SQL for a Microsoft SQL Server database.

DATABASE SCHEMA (authoritative source of truth):
{SCHEMA_SUMMARY}

ABSOLUTE RULES (YOU MUST OBEY ALL OF THESE):
- Use ONLY tables and columns that appear in the schema above.
- ALWAYS use schema-qualified table names exactly as shown in the schema summary.
  For example: Sales.Customers, Sales.Orders, Sales.OrderLines, Warehouse.StockItems, etc.
- NEVER invent table or column names or schemas. If a schema name (like Production, Manufacturing, or Products)
  does not appear in the schema summary, DO NOT use it.
- Prefer the Sales.* and Warehouse.* schemas for business metrics like orders, invoices, customers, and stock items.
- When working with product categories or stock groups, ALWAYS join Warehouse.StockItems to Warehouse.StockGroups THROUGH Warehouse.StockItemStockGroups (i.e., StockItems → StockItemStockGroups → StockGroups). NEVER join StockItems directly to StockGroups.
- If the question mentions "products" or "product categories", favour tables like Warehouse.StockItems and
  any related StockGroups tables that appear in the schema summary, NOT fictional tables like Production.Products.
- Use ONLY SELECT (read-only). No INSERT, UPDATE, DELETE, MERGE, or DDL.
- Use TOP to limit rows when returning detailed lists.
- Prefer aggregated queries (GROUP BY) when summarisation is implied.
- Avoid CROSS JOIN unless absolutely required.
- Do NOT include comments.
- Do NOT wrap the query in markdown code fences.
- Respond with ONLY the raw SQL query, nothing else.

Business question to answer (in English):
{question!r}
"""

    raw_sql = llm(sql_prompt)
    sql = _clean_sql_output(raw_sql)

    try:
        rows: List[dict] = run_query(sql)
    except Exception as e:
        # If execution fails, return the error and the raw SQL to the UI
        return {
            "answer": (
                "⚠️ There was an error executing the generated SQL.\n\n"
                f"Error:\n{e}\n\n"
                "Generated SQL:\n"
                f"```sql\n{sql or raw_sql}\n```"
            ),
            "rows": [],
            "sql": sql or raw_sql,
        }

    explain_prompt = f"""
You are an analytics copilot explaining query results to a business stakeholder.

Business question:
{question!r}

SQL used:
```sql
{sql}
```

Result rows (up to 30 shown):
{rows[:30]}

Explain the key insights clearly and concisely:
- Start with a 2–3 sentence summary.
- Then list 3–7 bullet points highlighting the most important numbers, trends, or anomalies.
- If it makes sense, compare segments, products, or time periods.
- Avoid technical jargon; focus on the "so what?" for an analyst or manager.
"""
    answer_text = llm(explain_prompt)

    return {
        "answer": answer_text,
        "rows": rows,
        "sql": sql,
    }
