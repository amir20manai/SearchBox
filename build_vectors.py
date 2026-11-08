import os
import rag
from PyPDF2 import PdfReader
import docx

DOC_FOLDER = "documents"

def read_txt(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def read_pdf(path):
    text = ""
    reader = PdfReader(path)
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def read_docx(path):
    doc = docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def read_file(path):
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext == ".txt":  return read_txt(path)
    if ext == ".pdf":  return read_pdf(path)
    if ext == ".docx": return read_docx(path)
    return ""

print("🚀 Début de la construction de la base de données vectorielle...")

count = 0
for filename in sorted(os.listdir(DOC_FOLDER)):
    path = os.path.join(DOC_FOLDER, filename)
    if not os.path.isfile(path):
        continue

    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".txt", ".pdf", ".docx"}:
        continue

    print(f"📄 Traitement : {filename}")
    try:
        contenu = read_file(path)
        if contenu.strip():
            success = rag.add_document_to_vector_db(filename, contenu)
            if success:
                count += 1
    except Exception as e:
        print(f"  ❌ Erreur : {e}")

print(f"\n✅ Terminé ! {count} document(s) ajouté(s) à la base de données vectorielle.")