import streamlit as st
import tempfile
import json
import os
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


def calculate_similarity(trans1, trans2):
    min_len = min(len(trans1), len(trans2))
    scores = []

    for i in range(min_len):

        t1 = trans1[i]
        t2 = trans2[i]

        desc_sim = similarity(t1.get("details", ""), t2.get("details", ""))

        date_match = 1 if t1.get("date") == t2.get("date") else 0

        amt1 = t1.get("credit", 0) if t1.get("credit", 0) != 0 else t1.get("debit", 0)
        amt2 = t2.get("amount", 0)
        amount_match = 1 if float(amt1) == float(amt2) else 0

        balance_match = 1 if float(t1.get("balance", 0)) == float(t2.get("balance", 0)) else 0

        total = (date_match + amount_match + balance_match + desc_sim) / 4
        scores.append(total)

    if scores:
        return round((sum(scores) / len(scores)) * 100, 2)
    return 0


# ----------------------------
# UI
# ----------------------------
st.title("AI Expense Tracker - Validation Engine")

uploaded_file = st.file_uploader("Upload Bank Statement PDF", type=["pdf"])

if uploaded_file:

    password = st.text_input("Enter PDF Password (if any)", type="password")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        pdf_path = tmp_file.name

    if st.button("Run Validation"):

        # ----------------------------
        # Select Active Parser
        # ----------------------------
        if os.path.exists("manual_override_parser.py"):
            st.info("🔁 Using Manual Override Parser")
            parser_file = "manual_override_parser.py"
        else:
            st.info("⚙ Using Generated Parser")
            parser_file = "generated_parser.py"

        # ----------------------------
        # Run Code Parser
        # ----------------------------
        code_transactions = execute_parser(pdf_path, parser_file, password)
        st.success(f"Code Parser Transactions: {len(code_transactions)}")

        # ----------------------------
        # Run LLM Direct Extraction
        # ----------------------------
        llm_response = parse_with_llm(pdf_path, password)
        llm_transactions = extract_json_from_response(llm_response)
        st.success(f"LLM Transactions: {len(llm_transactions)}")

        # ----------------------------
        # Side-by-Side Comparison
        # ----------------------------
        st.subheader("Side-by-Side Comparison")

        min_len = min(len(code_transactions), len(llm_transactions))
        transaction_scores = []

        for i in range(min_len):

            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"### Code Parser - Transaction {i+1}")
                st.json(code_transactions[i])

            with col2:
                st.markdown(f"### LLM Parser - Transaction {i+1}")
                st.json(llm_transactions[i])

            # Transaction Similarity
            desc_sim = similarity(
                code_transactions[i].get("details", ""),
                llm_transactions[i].get("details", "")
            )

            date_match = 1 if code_transactions[i].get("date") == llm_transactions[i].get("date") else 0

            amt1 = code_transactions[i].get("credit", 0) if code_transactions[i].get("credit", 0) != 0 else code_transactions[i].get("debit", 0)
            amt2 = llm_transactions[i].get("amount", 0)
            amount_match = 1 if float(amt1) == float(amt2) else 0

            balance_match = 1 if float(code_transactions[i].get("balance", 0)) == float(llm_transactions[i].get("balance", 0)) else 0

            total = (date_match + amount_match + balance_match + desc_sim) / 4
            percent = round(total * 100, 2)

            transaction_scores.append(total)

            st.info(f"Transaction Similarity: {percent}%")
            st.divider()

        # ----------------------------
        # Overall Similarity
        # ----------------------------
        if transaction_scores:
            overall_similarity = round((sum(transaction_scores) / len(transaction_scores)) * 100, 2)

            st.subheader("Overall Similarity")
            st.success(f"Similarity Score: {overall_similarity}%")

            # ==================================================
            # DECISION ENGINE
            # ==================================================

            # CASE 1: ≥ 90%
            if overall_similarity >= 90:
                st.success("✅ ACCEPTED")
                st.success("🚀 Parser Verified & Deployed")

            # CASE 2: 75–90% (Human Loop)
            elif 75 <= overall_similarity < 90:

                st.warning("⚠ PARTIAL MATCH (75–90%)")
                st.info("👨‍💻 Human Intervention Required")

                manual_code = st.text_area(
                    "Write Manual Parser Code Below:",
                    height=400,
                    placeholder="def parse_pdf(pdf_path, password=None):\n    # your logic\n    return transactions"
                )

                if st.button("Validate Human Code"):

                    if manual_code.strip() == "":
                        st.error("Code cannot be empty.")

                    elif "def parse_pdf" not in manual_code:
                        st.error("Code must contain: def parse_pdf(pdf_path, password=None):")

                    else:
                        try:
                            # Save temp file
                            with open("temp_manual_parser.py", "w", encoding="utf-8") as f:
                                f.write(manual_code)

                            st.info("🔄 Running Human Parser...")

                            human_transactions = execute_parser(pdf_path, "temp_manual_parser.py", password)

                            human_similarity = calculate_similarity(human_transactions, llm_transactions)

                            st.success(f"Human Parser Similarity: {human_similarity}%")

                            if human_similarity >= 90:

                                with open("manual_override_parser.py", "w", encoding="utf-8") as f:
                                    f.write(manual_code)

                                st.success("✅ HUMAN CODE ACCEPTED")
                                st.success("🚀 Manual Parser is now ACTIVE")

                            else:
                                st.error("❌ HUMAN CODE REJECTED (Below 90%)")

                        except Exception as e:
                            st.error(f"Execution Error: {e}")

            # CASE 3: < 75%
            else:
                st.error("❌ REJECTED (Below 75%)")

        # Optional Deactivation
        if os.path.exists("manual_override_parser.py"):
            st.divider()
            if st.button("Deactivate Manual Override"):
                os.remove("manual_override_parser.py")
                st.success("Manual Override Removed")
