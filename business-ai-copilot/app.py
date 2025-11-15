import streamlit as st
import pandas as pd
from ai.sql_agent import answer_from_sql

st.set_page_config(page_title="Business SQL Insights Copilot", layout="wide")
st.title("🧠 Business SQL Insights Copilot")

st.markdown(
    """
    Ask natural language questions about the **SQL Server database**.

    Examples:
    - "Which customers have the highest total order value in the last 6 months?"
    - "Show total sales by month for the last 2 years."
    - "Which product categories contribute most to revenue?"
    """
)

if "history" not in st.session_state:
    st.session_state.history = []
if "last_sql_result" not in st.session_state:
    st.session_state.last_sql_result = None

user_q = st.chat_input("Ask your question about the business data...")

if user_q:
    st.session_state.history.append(("user", user_q))

    with st.spinner("Querying the database and analysing results..."):
        sql_result = answer_from_sql(user_q)
        ans_text = sql_result["answer"]

    st.session_state.history.append(("assistant", ans_text))
    st.session_state.last_sql_result = sql_result

# Chat history display
for role, msg in st.session_state.history:
    with st.chat_message(role):
        st.markdown(msg)

# If we have SQL rows from the last query, show them with simple visuals
sql_res = st.session_state.last_sql_result
if sql_res is not None:
    rows = sql_res.get("rows", [])
    sql = sql_res.get("sql", "")

    if rows:
        st.markdown("### 📊 Data behind the insight")
        if sql:
            st.code(sql, language="sql")

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # Try a simple chart if there's at least one numeric column with a valid name
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        # Filter out empty or whitespace-only column names that can break Altair/Streamlit
        numeric_cols = [c for c in numeric_cols if c and str(c).strip()]

        if numeric_cols:
            st.markdown("#### Quick visual (first numeric column)")
            st.line_chart(df[numeric_cols[0]])
