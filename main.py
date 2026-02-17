from pdf_input import open_pdf
from executor import execute_parser
from llm_parser import parse_with_llm
import json
import re
from difflib import SequenceMatcher


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================
def extract_json_from_response(response_text):

    response_text = response_text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            return []
    return []


def calculate_similarity(a, b):
    return SequenceMatcher(None, str(a), str(b)).ratio()


def validate_transactions(code_txns, llm_txns):

    min_length = min(len(code_txns), len(llm_txns))

    if min_length == 0:
        return None

    date_matches = 0
    amount_matches = 0
    balance_matches = 0
    description_scores = []

    for i in range(min_length):

        code = code_txns[i]
        llm = llm_txns[i]

        # Date match
        if str(code.get("date")) == str(llm.get("date")):
            date_matches += 1

        # Amount match
        code_amount = code.get("debit", 0) or code.get("credit", 0)
        llm_amount = llm.get("amount", 0)

        if abs(float(code_amount) - float(llm_amount)) < 1:
            amount_matches += 1

        # Balance match
        if abs(float(code.get("balance", 0)) - float(llm.get("balance", 0))) < 1:
            balance_matches += 1

        # Description similarity
        desc_similarity = calculate_similarity(
            code.get("details", ""),
            llm.get("details", "")
        )
        description_scores.append(desc_similarity)

    total = min_length

    date_accuracy = (date_matches / total) * 100
    amount_accuracy = (amount_matches / total) * 100
    balance_accuracy = (balance_matches / total) * 100
    description_accuracy = (sum(description_scores) / total) * 100

    overall_accuracy = (
        date_accuracy +
        amount_accuracy +
        balance_accuracy +
        description_accuracy
    ) / 4

    return {
        "date_accuracy": round(date_accuracy, 2),
        "amount_accuracy": round(amount_accuracy, 2),
        "balance_accuracy": round(balance_accuracy, 2),
        "description_accuracy": round(description_accuracy, 2),
        "overall_accuracy": round(overall_accuracy, 2),
    }


# ==========================================================
# MAIN EXECUTION
# ==========================================================
print("\n=========== AI EXPENSE TRACKER ===========\n")

pdf_path, password = open_pdf()

# ---------------- PHASE 1 ----------------
parser_path = "generated_parser.py"
code_transactions = execute_parser(pdf_path, parser_path, password)

print("\n✅ Code Parser Transactions:", len(code_transactions))

# ---------------- PHASE 2 ----------------
print("\n🔵 Sending PDF to LLM...")

llm_response = parse_with_llm(pdf_path, password)
llm_transactions = extract_json_from_response(llm_response)

print("✅ LLM Transactions:", len(llm_transactions))

# ---------------- VALIDATION ----------------
print("\n=========== VALIDATION ===========")

if len(code_transactions) == len(llm_transactions):
    print("✅ Transaction count MATCHED")
else:
    print("❌ Transaction count MISMATCH")

metrics = validate_transactions(code_transactions, llm_transactions)

if metrics:
    print("\n--- Detailed Accuracy ---")
    print(f"Date Match Accuracy: {metrics['date_accuracy']}%")
    print(f"Amount Match Accuracy: {metrics['amount_accuracy']}%")
    print(f"Balance Match Accuracy: {metrics['balance_accuracy']}%")
    print(f"Description Similarity: {metrics['description_accuracy']}%")
    print(f"\nOverall Extraction Accuracy: {metrics['overall_accuracy']}%")
else:
    print("❌ Unable to compute accuracy (no transactions).")

print("\n===================================")
