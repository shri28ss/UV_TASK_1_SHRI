import pdfplumber

with pdfplumber.open("statement.pdf", password="SHRID28052004") as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n----- PAGE {i+1} -----\n")
        print(page.extract_text())
        break
