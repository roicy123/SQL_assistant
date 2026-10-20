import os

import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://127.0.0.1:8000/ask")
st.title("Sales Data Assistant")
st.caption("Ask a question about customers, products and orders. The generated SQL is always shown.")

q = st.text_input("Your question", placeholder="Which product category earned the most revenue?")
if q:
    try:
        resp = requests.post(API, json={"question": q}, timeout=90)
        resp.raise_for_status()
        r = resp.json()
    except requests.RequestException:
        st.error("The assistant is unavailable right now. Please try again.")
        st.stop()

    if r["error"]:
        st.warning(r["error"])
    else:
        st.write(r["summary"])
        st.dataframe(pd.DataFrame(r["rows"], columns=r["columns"]), use_container_width=True)
    with st.expander("Generated SQL"):
        st.code(r["sql"], language="sql")
        st.caption(f"Attempts: {r['attempts']}")