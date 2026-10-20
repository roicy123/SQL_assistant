import sqlite3

import pytest

from app.sql_guard import GuardError, connect_readonly, run_select, validate


@pytest.mark.parametrize("sql", [
    "DROP TABLE orders",
    "DELETE FROM orders",
    "SELECT 1; DROP TABLE orders",
    "UPDATE products SET price = 1",
    "PRAGMA table_info(orders)",
    "WITH x AS (SELECT 1) DELETE FROM orders",
    "",
])
def test_rejects_unsafe(sql):
    with pytest.raises(GuardError):
        validate(sql)


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM orders",
    "select * from customers where city = 'Kochi';",
    "WITH t AS (SELECT * FROM orders) SELECT COUNT(*) FROM t",
])
def test_accepts_select(sql):
    assert validate(sql)


def test_readonly_connection_blocks_writes_even_without_validator():
    conn = connect_readonly()
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM orders")


def test_run_select_returns_rows():
    cols, rows = run_select("SELECT COUNT(*) FROM customers")
    assert rows == [(40,)]