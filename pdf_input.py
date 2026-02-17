from getpass import getpass
import pdfplumber

def open_pdf():
    filename = input("Enter PDF filename (with .pdf): ").strip()
    password = input("Enter PDF password (leave blank if none): ")


    try:
        if password:
            pdfplumber.open(filename, password=password)
        else:
            pdfplumber.open(filename)
    except Exception:
        raise ValueError("❌ Incorrect password or unreadable PDF")

    print("✅ PDF opened successfully")
    return filename, password
