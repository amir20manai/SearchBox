"""
indexer.py — Indexe tous les fichiers du dossier `documents/` dans Whoosh.
"""
import os
import datetime
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, DATETIME

from PyPDF2 import PdfReader
import docx

INDEX_DIR  = "indexdir"
DOC_FOLDER = "documents"

os.makedirs(INDEX_DIR,  exist_ok=True)
os.makedirs(DOC_FOLDER, exist_ok=True)

# ✅ الـ Schema فيه التاريخ
schema = Schema(
    id=ID(stored=True, unique=True),
    titre=TEXT(stored=True),
    contenu=TEXT(stored=True),
    date=DATETIME(stored=True, sortable=True),
)

if exists_in(INDEX_DIR):
    print(f"📂 Index existant trouvé dans '{INDEX_DIR}' → ouverture.")
    ix = open_dir(INDEX_DIR)
else:
    print(f"🆕 Aucun index trouvé → création dans '{INDEX_DIR}'.")
    ix = create_in(INDEX_DIR, schema)

writer = ix.writer()

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

indexed = 0
skipped = 0
errors  = 0

for filename in sorted(os.listdir(DOC_FOLDER)):
    path = os.path.join(DOC_FOLDER, filename)
    if not os.path.isfile(path):
        continue

    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".txt", ".pdf", ".docx"}:
        print(f"  ⏭  Ignoré (format non supporté) : {filename}")
        skipped += 1
        continue

    print(f"📄 Indexation : {filename}")

    try:
        contenu = read_file(path)
    except Exception as e:
        print(f"  ❌ Erreur de lecture : {e}")
        errors += 1
        continue

    if not contenu.strip():
        print(f"  ⚠  Ignoré (vide ou illisible) : {filename}")
        skipped += 1
        continue

    # ✅ ناخذو تاريخ الملف و نبعثوه للـ index
    mtime = os.path.getmtime(path)
    file_date = datetime.datetime.fromtimestamp(mtime)

    writer.update_document(
        id=filename, 
        titre=filename, 
        contenu=contenu,
        date=file_date
    )
    indexed += 1

writer.commit()

print()
print("─" * 50)
print(f"✅ Terminé : {indexed} fichier(s) indexé(s)")
if skipped:
    print(f"⏭  {skipped} fichier(s) ignoré(s)")
if errors:
    print(f"❌ {errors} erreur(s) de lecture")
print("─" * 50)
