"""Two independent safety layers: a SELECT-only validator and a read-only database connection."""
import os
import re
import sqlite3

DB_PATH = os.getenv("SALES_DB", "sales.db")
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|truncate|vacuum)\b", re.I)


class GuardError(ValueError):
    """Raised when a query is rejected before it reaches the database."""


def validate(sql):
    s = sql.strip().rstrip(";").strip()
    if not s:
        raise GuardError("empty query")
    if ";" in s:
        raise GuardError("multiple statements are not allowed")
    if not re.match(r"^(select|with)\b", s, re.I):
        raise GuardError("only SELECT queries are allowed")
    if FORBIDDEN.search(s):
        raise GuardError("query contains a forbidden keyword")
    return s


def connect_readonly(path=DB_PATH):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def run_select(sql, path=DB_PATH, limit=200):
    sql = validate(sql)
    conn = connect_readonly(path)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchmany(limit)
    finally:
        conn.close()


def get_schema(path=DB_PATH):
    conn = connect_readonly(path)
    try:
        rows = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    finally:
        conn.close()
    return "\n".join(r[0].strip() for r in rows)