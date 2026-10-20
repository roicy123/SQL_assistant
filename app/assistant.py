import os
import re
import sqlite3

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.sql_guard import GuardError, get_schema, run_select

load_dotenv()
llm = ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), temperature=0)

REFUSAL = "CANNOT_ANSWER"

RULES = (
    "You are a careful SQLite expert. Write exactly ONE read-only SQLite SELECT query that answers the question. "
    "Use only the tables and columns in the schema. Dates are stored as 'YYYY-MM-DD' text. "
    "Revenue means quantity * unit_price from order_items. "
    "Order status is one of 'completed', 'cancelled', 'returned'. "
    "Return only the SQL: no explanation, no markdown. "
    f"If the request asks you to change data, or is not a question about this data, return exactly: {REFUSAL}"
)

# Examples for the few-shot variant. They must NOT appear in eval/questions.json.
FEW_SHOT = [
    ("How many products are in the Home category?",
     "SELECT COUNT(*) FROM products WHERE category = 'Home'"),
    ("What is the total quantity of items ordered in June 2025?",
     "SELECT SUM(oi.quantity) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id "
     "WHERE o.order_date >= '2025-06-01' AND o.order_date < '2025-07-01'"),
    ("Which customer placed the most orders?",
     "SELECT c.name, COUNT(*) AS n FROM customers c JOIN orders o ON o.customer_id = c.customer_id "
     "GROUP BY c.customer_id ORDER BY n DESC LIMIT 1"),
]


def clean_sql(text):
    text = text.strip()
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip()


def generate_sql(question, few_shot=True, prev_sql=None, error=None):
    system = RULES + "\n\nSchema:\n" + get_schema()
    if few_shot:
        system += "\n\nExamples:\n" + "\n".join(f"Question: {q}\nSQL: {s}" for q, s in FEW_SHOT)
    user = f"Question: {question}"
    if prev_sql and error:
        user += f"\n\nYour previous query failed.\nQuery: {prev_sql}\nError: {error}\nReturn a corrected query."
    reply = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return clean_sql(reply.content)


def sql_with_retry(question, few_shot=True):
    """Returns (sql, columns, rows, error, attempts). Guard rejections are never retried."""
    sql = generate_sql(question, few_shot)
    for attempt in (1, 2):
        if sql.strip().upper() == REFUSAL:
            return sql, [], [], "I can only answer read-only questions about the sales data.", attempt
        try:
            cols, rows = run_select(sql)
            return sql, cols, rows, None, attempt
        except GuardError as e:
            return sql, [], [], f"Blocked: {e}", attempt
        except sqlite3.Error as e:
            if attempt == 2:
                return sql, [], [], f"SQL error: {e}", attempt
            sql = generate_sql(question, few_shot, prev_sql=sql, error=str(e))


def summarize(question, cols, rows):
    shown = rows[:20]
    prompt = (f"Question: {question}\nColumns: {cols}\nRows (first {len(shown)} of {len(rows)}): {shown}\n"
              "Answer the question in one or two sentences using only these rows.")
    return llm.invoke([SystemMessage(content="You explain database query results briefly and accurately. "
                                             "All monetary amounts are in Indian rupees (Rs.); never use a dollar sign."),
                       HumanMessage(content=prompt)]).content.strip()


def answer(question, few_shot=True):
    sql, cols, rows, error, attempts = sql_with_retry(question, few_shot)
    summary = None if error else summarize(question, cols, rows)
    return {"question": question, "sql": sql, "columns": cols, "rows": rows,
            "summary": summary, "error": error, "attempts": attempts}