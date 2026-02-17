import streamlit as st
import tempfile
import json
from executor import execute_parser
from llm_parser import parse_with_llm
from difflib import SequenceMatcher
import re


# ----------------------------
# Helper Functions
# ----------------------------
def extract_json_from_response(response_text):
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            return []
    return []


def similarity(a, b):
    return SequenceMatcher(None, str(a), str(b)).ratio()


# ----------------------------
# UI Layout
# ----------------------------
st.title("AI Expense Tracker - Parser Comparison")

uploaded_file = st.file_uploader("Upload Bank Statement PDF", type=["pdf"])

if uploaded_file:

    password = st.text_input("Enter PDF Password (if any)", type="password")

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    if st.button("Run Comparison"):

        st.subheader("Running Phase 1: Code Parser")
        code_transactions = execute_parser(pdf_path, "generated_parser.py", password)
        st.success(f"Code Parser Transactions: {len(code_transactions)}")

        st.subheader("Running Phase 2: LLM Parser")
        llm_response = parse_with_llm(pdf_path, password)
        llm_transactions = extract_json_from_response(llm_response)
        st.success(f"LLM Transactions: {len(llm_transactions)}")

        st.subheader("Transaction Count Validation")

        if len(code_transactions) == len(llm_transactions):
            st.success("Transaction count MATCHED")
        else:
            st.error("Transaction count MISMATCH")

        # ----------------------------
        # Side-by-Side Comparison
        # ----------------------------
        st.subheader("Side-by-Side Comparison")

        min_len = min(len(code_transactions), len(llm_transactions))

        for i in range(min_len):

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"### Code Parser - Transaction {i+1}")
                st.json(code_transactions[i])

            with col2:
                st.markdown(f"### LLM Parser - Transaction {i+1}")
                st.json(llm_transactions[i])

            # Similarity
            desc_sim = similarity(
                code_transactions[i].get("details", ""),
                llm_transactions[i].get("details", "")
            )

            st.info(f"Description Similarity: {round(desc_sim * 100, 2)}%")

            st.divider()
