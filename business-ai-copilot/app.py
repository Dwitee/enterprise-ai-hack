import streamlit as st
import pandas as pd
from ai.sql_agent import answer_from_sql
from db.database import run_query, get_schema_summary

st.set_page_config(page_title="Business SQL Insights Copilot", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def get_overview_data():
    """
    Pre-compute high-level business metrics and simple time-series
    directly from the SQL Server database.
    """
    metrics = {
        "total_customers": None,
        "total_orders": None,
        "total_invoices": None,
        "total_revenue": None,
        "revenue_last_12m": None,
        "top_stock_group": None,
        "top_stock_group_revenue": None,
    }
    monthly_revenue_df = None
    monthly_orders_df = None

    # Total customers
    try:
        rows = run_query("SELECT COUNT(*) AS TotalCustomers FROM Sales.Customers;")
        metrics["total_customers"] = rows[0]["TotalCustomers"]
    except Exception:
        pass

    # Total orders
    try:
        rows = run_query("SELECT COUNT(*) AS TotalOrders FROM Sales.Orders;")
        metrics["total_orders"] = rows[0]["TotalOrders"]
    except Exception:
        pass

    # Total invoices and total revenue (all time)
    try:
        rows = run_query("SELECT COUNT(*) AS TotalInvoices FROM Sales.Invoices;")
        metrics["total_invoices"] = rows[0]["TotalInvoices"]
    except Exception:
        pass

    try:
        rows = run_query(
            """
            SELECT SUM(Quantity * UnitPrice) AS TotalRevenue
            FROM Sales.InvoiceLines;
            """
        )
        metrics["total_revenue"] = rows[0]["TotalRevenue"]
    except Exception:
        pass

    # Revenue in last 12 months (relative to latest invoice date in the dataset)
    try:
        rows = run_query(
            """
            WITH Latest AS (
                SELECT MAX(InvoiceDate) AS MaxDate
                FROM Sales.Invoices
            )
            SELECT
                SUM(il.Quantity * il.UnitPrice) AS RevenueLast12M
            FROM Sales.InvoiceLines AS il
            JOIN Sales.Invoices AS i
                ON il.InvoiceID = i.InvoiceID
            CROSS JOIN Latest
            WHERE i.InvoiceDate >= DATEADD(month, -12, Latest.MaxDate);
            """
        )
        metrics["revenue_last_12m"] = rows[0]["RevenueLast12M"]
    except Exception:
        pass

    # Top stock group by revenue
    try:
        rows = run_query(
            """
            SELECT TOP 1
                sg.StockGroupName,
                SUM(il.Quantity * il.UnitPrice) AS TotalRevenue
            FROM Sales.InvoiceLines AS il
            JOIN Warehouse.StockItemStockGroups AS sisg
                ON il.StockItemID = sisg.StockItemID
            JOIN Warehouse.StockGroups AS sg
                ON sisg.StockGroupID = sg.StockGroupID
            GROUP BY sg.StockGroupName
            ORDER BY TotalRevenue DESC;
            """
        )
        if rows:
            metrics["top_stock_group"] = rows[0]["StockGroupName"]
            metrics["top_stock_group_revenue"] = rows[0]["TotalRevenue"]
    except Exception:
        pass

    # Monthly revenue for last 12 months (relative to latest invoice date)
    try:
        rows = run_query(
            """
            WITH Latest AS (
                SELECT MAX(InvoiceDate) AS MaxDate
                FROM Sales.Invoices
            )
            SELECT
                FORMAT(i.InvoiceDate, 'yyyy-MM') AS Month,
                SUM(il.Quantity * il.UnitPrice) AS Revenue
            FROM Sales.InvoiceLines AS il
            JOIN Sales.Invoices AS i
                ON il.InvoiceID = i.InvoiceID
            CROSS JOIN Latest
            WHERE i.InvoiceDate >= DATEADD(month, -12, Latest.MaxDate)
            GROUP BY FORMAT(i.InvoiceDate, 'yyyy-MM')
            ORDER BY Month;
            """
        )
        if rows:
            monthly_revenue_df = pd.DataFrame(rows)
    except Exception:
        pass

    # Orders per month for last 12 months (relative to latest order date)
    try:
        rows = run_query(
            """
            WITH Latest AS (
                SELECT MAX(OrderDate) AS MaxDate
                FROM Sales.Orders
            )
            SELECT
                FORMAT(o.OrderDate, 'yyyy-MM') AS Month,
                COUNT(*) AS Orders
            FROM Sales.Orders AS o
            CROSS JOIN Latest
            WHERE o.OrderDate >= DATEADD(month, -12, Latest.MaxDate)
            GROUP BY FORMAT(o.OrderDate, 'yyyy-MM')
            ORDER BY Month;
            """
        )
        if rows:
            monthly_orders_df = pd.DataFrame(rows)
    except Exception:
        pass

    return {
        "metrics": metrics,
        "monthly_revenue": monthly_revenue_df,
        "monthly_orders": monthly_orders_df,
    }


def render_schema_view():
    """
    Render a simple, human-friendly view of the main tables and relationships
    so users can understand the data model before asking questions.
    """
    st.subheader("📚 Schema & table relationships")

    st.markdown(
        """
        The WideWorldImporters database is organised into a few key schemas:

        - **Sales** – customers, orders, invoices and line items (transactional data)
        - **Warehouse** – stock items, stock groups and product metadata
        - **Application** – cities, people and reference data
        """
    )

    st.markdown("#### Sales schema (transactions)")
    st.markdown(
        """
        - **Sales.Customers** – one row per customer (CustomerID, CustomerName, BillToCustomerID, etc.)
        - **Sales.Orders** – one row per order (OrderID, CustomerID, OrderDate, etc.)
        - **Sales.OrderLines** – line items for each order (OrderLineID, OrderID, StockItemID, Quantity, UnitPrice)
        - **Sales.Invoices** – one row per invoice (InvoiceID, CustomerID, InvoiceDate, etc.)
        - **Sales.InvoiceLines** – line items for each invoice (InvoiceLineID, InvoiceID, StockItemID, Quantity, UnitPrice)
        """
    )

    st.markdown("#### Warehouse schema (products)")
    st.markdown(
        """
        - **Warehouse.StockItems** – one row per product/stock item (StockItemID, StockItemName, UnitPrice, etc.)
        - **Warehouse.StockGroups** – high-level product groups/categories (StockGroupID, StockGroupName)
        - **Warehouse.StockItemStockGroups** – link table mapping stock items to stock groups (StockItemID, StockGroupID)
        """
    )

    st.markdown("#### Application schema (locations & reference)")
    st.markdown(
        """
        - **Application.Cities**, **Application.StateProvinces**, **Application.Countries**
          – location metadata that can be joined to customers, suppliers, etc.
        """
    )

    st.markdown("#### Key relationships (box diagram style)")
    st.code(
        """
[Sales.Customers] 1 ──< [Sales.Orders] 1 ──< [Sales.OrderLines]
       │
       └──< [Sales.Invoices] 1 ──< [Sales.InvoiceLines]

[Warehouse.StockItems] 1 ──< [Sales.OrderLines / Sales.InvoiceLines]

[Warehouse.StockItems] 1 ──< [Warehouse.StockItemStockGroups] >── 1 [Warehouse.StockGroups]
        """.strip()
    )

    st.markdown("#### Visual schema diagram")

    dot = r"""
digraph G {
    rankdir=LR;
    node [shape=box, style=filled, fillcolor="#f5f5f5", color="#888888", fontname="Helvetica"];

    Sales_Customers         [label="Sales.Customers"];
    Sales_Orders            [label="Sales.Orders"];
    Sales_OrderLines        [label="Sales.OrderLines"];
    Sales_Invoices          [label="Sales.Invoices"];
    Sales_InvoiceLines      [label="Sales.InvoiceLines"];

    Warehouse_StockItems           [label="Warehouse.StockItems"];
    Warehouse_StockItemStockGroups [label="Warehouse.StockItemStockGroups"];
    Warehouse_StockGroups          [label="Warehouse.StockGroups"];

    // Sales relationships
    Sales_Customers -> Sales_Orders       [label="CustomerID"];
    Sales_Orders    -> Sales_OrderLines   [label="OrderID"];
    Sales_Customers -> Sales_Invoices     [label="CustomerID"];
    Sales_Invoices  -> Sales_InvoiceLines [label="InvoiceID"];

    // Product relationships
    Warehouse_StockItems -> Sales_OrderLines   [label="StockItemID"];
    Warehouse_StockItems -> Sales_InvoiceLines [label="StockItemID"];

    // Stock group relationships
    Warehouse_StockItems           -> Warehouse_StockItemStockGroups [label="StockItemID"];
    Warehouse_StockItemStockGroups -> Warehouse_StockGroups          [label="StockGroupID"];
}
    """

    st.graphviz_chart(dot)

    st.markdown(
        """
        You can use these relationships to phrase better questions, for example:

        - *"Show total revenue per stock group using invoice lines and stock item stock groups."*
        - *"For each customer, show total orders and total invoice revenue per year."*
        """
    )

    # Optionally show a trimmed version of the raw schema summary for power users
    try:
        schema_text = get_schema_summary()
        with st.expander("Full raw schema summary (truncated)"):
            st.text(schema_text[:4000])
    except Exception:
        pass


st.title("PEPSACO DB Insights Copilot")

# Simple left-hand navigation
view = st.sidebar.radio(
    "Navigation",
    ("Overview & Copilot", "Schema & Tables"),
    index=0,
)

st.markdown(
    """
    This is your **Business Overview** and **AI-powered SQL copilot** over the
    WideWorldImporters SQL Server database.
    """
)

if view == "Schema & Tables":
    render_schema_view()
else:
    # ---------- Overview dashboard (landing screen) ----------
    overview = get_overview_data()
    metrics = overview["metrics"]

    st.subheader("Business overview")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total customers",
            f"{metrics['total_customers']:,}"
            if metrics["total_customers"] is not None
            else "—",
        )
        st.metric(
            "Total orders",
            f"{metrics['total_orders']:,}"
            if metrics["total_orders"] is not None
            else "—",
        )
    with col2:
        st.metric(
            "Total invoices",
            f"{metrics['total_invoices']:,}"
            if metrics["total_invoices"] is not None
            else "—",
        )
        st.metric(
            "Total revenue (all time)",
            f"{metrics['total_revenue']:.0f}"
            if metrics["total_revenue"] is not None
            else "—",
        )
    with col3:
        st.metric(
            "Revenue (last 12 months)",
            f"{metrics['revenue_last_12m']:.0f}"
            if metrics["revenue_last_12m"] is not None
            else "—",
        )
        if metrics["top_stock_group"]:
            st.metric(
                "Top stock group by revenue (all time)",
                metrics["top_stock_group"],
                f"{metrics['top_stock_group_revenue']:.0f}"
                if metrics["top_stock_group_revenue"] is not None
                else None,
            )
        else:
            st.metric("Top stock group by revenue (all time)", "—")

    # Mini charts row
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        if overview["monthly_revenue"] is not None:
            st.markdown("#### 📈 Monthly revenue (last 12 months)")
            st.line_chart(overview["monthly_revenue"].set_index("Month")["Revenue"])

    with chart_col2:
        if overview["monthly_orders"] is not None:
            st.markdown("#### 📦 Orders per month (last 12 months)")
            st.line_chart(overview["monthly_orders"].set_index("Month")["Orders"])

    st.markdown("---")

    # ---------- Natural language SQL copilot ----------
    st.markdown(
        """
        ### Ask questions in natural language

        Examples:
        - "Which customers placed the most orders?"
        - "Show total sales by month for the year 2016."
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
