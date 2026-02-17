import pdfplumber
import re
from typing import List, Dict


# ============================================================
# CORE LLM-GENERATED SBI PARSER (Integrated Properly)
# ============================================================

def extract_SBI_transactions(text: str) -> List[Dict]:

    # ------------------------------------------------------------
    # PRE-PROCESSING
    # ------------------------------------------------------------
    text = text.replace("\xa0", " ")
    raw_lines = text.splitlines()
    lines = [line.rstrip() for line in raw_lines]

    # ------------------------------------------------------------
    # CONFIGURATION & REGEX
    # ------------------------------------------------------------
    DATE_ANCHOR_REGEX = r'^\s*(?:\d+\s+)?(\d{1,2}[ \/\-](?:\d{1,2}|[A-Za-z]{3})[ \/\-]\d{2,4}|\d{4}-\d{2}-\d{2})'
    MONEY_REGEX = r'(\d+(?:,\d{2})*(?:,\d{3})*\.\d{2})'

    METADATA_KEYWORDS = [
        "Customer ID", "Account Number", "IFSC", "MICR",
        "Joint Holders", "Branch", "Statement From",
        "Nomination", "Currency", "Page ",
        "Digitally signed", "Generated on", "Date of Statement",
        "Clear Balance", "Monthly Avg Balance", "Account Status",
        "Account open Date", "Nominee Name", "Uncleared Amount",
        "CIF Number", "Product", "Lien", "Limit", "Interest Rate",
        "CKYCR Number", "Drawing Power"
    ]

    HEADER_LABELS = [
        "Txn Date", "Narration", "Withdrawals",
        "Deposits", "Closing Balance", "Brought Forward"
    ]

    TERMINATION_EXACT = {
        "GRAND TOTAL",
        "*** END OF STATEMENT ***",
        "END OF STATEMENT",
        "Abbreviations Used",
        "DISCLAIMER"
    }

    transactions = []
    current_txn = None

    # Detect initial balance
    initial_balance = 0.0
    bf_match = re.search(r'Brought Forward\(.*?\)\s+([\d,]+\.\d{2})(CR|DR)?', text, re.IGNORECASE)
    if bf_match:
        val = float(bf_match.group(1).replace(',', ''))
        initial_balance = -val if bf_match.group(2) == 'DR' else val

    # ------------------------------------------------------------
    # MAIN PARSING LOOP
    # ------------------------------------------------------------
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        if clean_line.upper() in TERMINATION_EXACT:
            break

        if clean_line.upper().startswith("ACCOUNT SUMMARY") and len(transactions) > 0:
            break

        date_match = re.match(DATE_ANCHOR_REGEX, line)

        if date_match:
            if current_txn:
                transactions.append(current_txn)

            date_str = date_match.group(1)

            money_matches = re.findall(MONEY_REGEX, line)
            amounts = [float(m.replace(',', '')) for m in money_matches]

            balance = amounts[-1] if amounts else 0.0
            debit = 0.0
            credit = 0.0

            if len(amounts) >= 3:
                debit = amounts[-3]
                credit = amounts[-2]
            elif len(amounts) == 2:
                tx_amt = amounts[0]
                if "DR" in line.upper() or "WDL" in line.upper():
                    debit = tx_amt
                elif "CR" in line.upper() or "DEP" in line.upper():
                    credit = tx_amt

            narr_text = line[date_match.end():].strip()
            for m in money_matches:
                narr_text = narr_text.replace(m, "", 1)

            narr_text = narr_text.replace(" . ", " ").replace(" - ", " ").strip()

            current_txn = {
                "date": date_str,
                "details": narr_text,
                "debit": debit,
                "credit": credit,
                "balance": balance,
                "confidence": 1.0 if (debit > 0 or credit > 0) else 0.5
            }

        elif current_txn:
            is_noise = any(k.upper() in clean_line.upper() for k in METADATA_KEYWORDS + HEADER_LABELS)

            if not is_noise and clean_line.upper() not in ["BALANCE", "DEP TFR", "WDL TFR", "TRANSFER"]:
                current_txn["details"] += " " + clean_line

    if current_txn:
        transactions.append(current_txn)

    # ------------------------------------------------------------
    # DYNAMIC MATH REPAIR
    # ------------------------------------------------------------
    for i in range(len(transactions)):
        curr = transactions[i]
        prev_bal = transactions[i-1]["balance"] if i > 0 else initial_balance
        delta = curr["balance"] - prev_bal

        if curr["debit"] == 0 and curr["credit"] == 0 and abs(delta) > 0.001:
            if delta > 0:
                curr["credit"] = abs(delta)
            else:
                curr["debit"] = abs(delta)
            curr["confidence"] = 0.8
        else:
            actual_diff = curr["credit"] - curr["debit"]
            if abs(actual_diff - delta) < 0.01:
                curr["confidence"] = 1.0
            else:
                curr["confidence"] = 0.8

    for txn in transactions:
        txn["details"] = " ".join(txn["details"].split()).strip()

    return transactions


# ============================================================
# REQUIRED ENTRY FUNCTION FOR YOUR SYSTEM
# ============================================================

def parse_pdf(pdf_path, password=None):

    full_text = ""

    if password:
        pdf = pdfplumber.open(pdf_path, password=password)
    else:
        pdf = pdfplumber.open(pdf_path)

    with pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    transactions = extract_SBI_transactions(full_text)

    return transactions
