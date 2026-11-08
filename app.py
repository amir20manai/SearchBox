import os
import re
import csv
import io
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, Response, jsonify
from werkzeug.utils import secure_filename
from markupsafe import escape, Markup
from whoosh.index import open_dir, create_in, exists_in
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.qparser import MultifieldParser, QueryParser, FuzzyTermPlugin
from whoosh import highlight

from PyPDF2 import PdfReader
import docx as python_docx

# ✅ نستوردو الـ RAG
import rag

app = Flask(__name__)
app.secret_key = "searchbox_secret"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

INDEX_DIR    = "indexdir"
DOC_FOLDER   = "documents"
UPLOAD_FOLDER = DOC_FOLDER
ALLOWED_EXT  = {".txt", ".pdf", ".docx"}

os.makedirs(INDEX_DIR, exist_ok=True)
os.makedirs(DOC_FOLDER, exist_ok=True)

schema = Schema(
    id=ID(stored=True, unique=True),
    titre=TEXT(stored=True),
    contenu=TEXT(stored=True),
    date=DATETIME(stored=True, sortable=True),
)

if exists_in(INDEX_DIR):
    ix = open_dir(INDEX_DIR)
else:
    ix = create_in(INDEX_DIR, schema)

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
    doc = python_docx.Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def read_file(path):
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext == ".txt":  return read_txt(path)
    if ext == ".pdf":  return read_pdf(path)
    if ext == ".docx": return read_docx(path)
    return ""

def index_file(path, filename):
    try:
        contenu = read_file(path)
    except Exception:
        return False

    if not contenu.strip():
        return False

    try:
        mtime = os.path.getmtime(path)
        file_date = datetime.datetime.fromtimestamp(mtime)

        writer = ix.writer()
        writer.update_document(
            id=filename, 
            titre=filename, 
            contenu=contenu,
            date=file_date
        )
        writer.commit()
        
        # ✅ نزيدو الملف للـ RAG (ChromaDB)
        rag.add_document_to_vector_db(filename, contenu)
        
        return True
    except Exception as e:
        print(f"❌ Erreur d'indexation {filename}: {e}")
        return False

@app.route("/")
def home():
    documents = []
    try:
        with ix.searcher() as s:
            for doc in s.all_stored_fields():
                if "titre" in doc:
                    documents.append({
                        "titre": doc["titre"],
                        "id":    doc.get("id", doc["titre"]),
                    })
        documents.sort(key=lambda d: d["titre"].lower())
    except Exception:
        pass

    total_files = len(documents)
    total_size = 0
    count_pdf = 0
    count_docx = 0
    count_txt = 0

    for doc in documents:
        path = os.path.join(UPLOAD_FOLDER, doc["titre"])
        if os.path.exists(path):
            total_size += os.path.getsize(path)

        ext = os.path.splitext(doc["titre"])[1].lower()
        if ext == ".pdf": count_pdf += 1
        elif ext == ".docx": count_docx += 1
        elif ext == ".txt": count_txt += 1

    total_size_mb = round(total_size / (1024 * 1024), 2)

    stats = {
        "total": total_files,
        "size_mb": total_size_mb,
        "pdf": count_pdf,
        "docx": count_docx,
        "txt": count_txt,
    }

    return render_template("index.html", documents=documents, stats=stats)


# ✅ صفحة الشات
@app.route("/chat")
def chat():
    # نقراو قائمة الملفات باش نحطوهم في القائمة المنسدلة (باش تختار مع شكون تحب تهدر)
    documents = []
    try:
        with ix.searcher() as s:
            for doc in s.all_stored_fields():
                if "titre" in doc:
                    documents.append(doc["titre"])
        documents.sort()
    except:
        pass
    return render_template("chat.html", documents=documents)


# ✅ الـ API إلّي يستنى في السؤال و يجاوب
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    question = data.get("question", "").strip()
    filename = data.get("filename", None) # إذا إختار ملف معين، وإلا None (باش يبحث في الكل)

    if not question:
        return jsonify({"error": "Question vide."}), 400

    result = rag.ask_documents(question, filename)

    if isinstance(result, str):
        # فمّا خطأ (ولا ما لقاش حاجة)
        return jsonify({"answer": result, "sources": []})
    else:
        return jsonify(result)


@app.route("/export")
def export_csv():
    documents = []
    try:
        with ix.searcher() as s:
            for doc in s.all_stored_fields():
                if "titre" in doc:
                    documents.append(doc["titre"])
        documents.sort(key=lambda t: t.lower())
    except Exception:
        pass

    output = io.StringIO()
    output.write('\ufeff')
    
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["Nom du fichier", "Type", "Taille (Ko)", "Date de modification"])

    for title in documents:
        path = os.path.join(UPLOAD_FOLDER, title)
        ext = os.path.splitext(title)[1].lower()
        
        size_ko = "0"
        date_str = "-"
        
        if os.path.exists(path):
            size_ko = str(round(os.path.getsize(path) / 1024, 1))
            mtime = os.path.getmtime(path)
            date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

        writer.writerow([title, ext.upper(), size_ko, date_str])

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=searchbox_documents.csv"}
    )


@app.route("/search", methods=["GET"])
def search():
    query_str = request.args.get("q", "").strip()
    field     = request.args.get("field", "both")
    doc_type  = request.args.get("type", "")
    sort_by   = request.args.get("sort", "pertinence")

    try:
        page = int(request.args.get("page", 1))
    except:
        page = 1
    page = max(1, page)

    per_page     = 10
    results_list = []
    total        = 0
    total_pages  = 1
    used_fuzzy   = False

    if query_str:
        with ix.searcher() as searcher:
            if field == "titre":
                parser = QueryParser("titre", ix.schema)
            elif field == "contenu":
                parser = QueryParser("contenu", ix.schema)
            else:
                parser = MultifieldParser(["titre", "contenu"], ix.schema)

            parser.add_plugin(FuzzyTermPlugin())

            sort_kwargs = {}
            if sort_by == "name_asc":
                sort_kwargs = {"sortedby": "titre"}
            elif sort_by == "name_desc":
                sort_kwargs = {"sortedby": "titre", "reverse": True}
            elif sort_by == "date_desc":
                sort_kwargs = {"sortedby": "date", "reverse": True}
            elif sort_by == "date_asc":
                sort_kwargs = {"sortedby": "date"}

            try:
                query = parser.parse(query_str)
                pager = searcher.search_page(query, pagenum=page, pagelen=per_page, **sort_kwargs)
                total = pager.total
            except Exception:
                total = 0
                pager = None

            if total == 0 and len(query_str) > 3:
                fuzzy_terms = " ".join(w + "~1" for w in query_str.split() if len(w) > 2)
                try:
                    fuzzy_query = parser.parse(fuzzy_terms)
                    pager = searcher.search_page(fuzzy_query, pagenum=page, pagelen=per_page, **sort_kwargs)
                    total = pager.total
                    used_fuzzy = True
                except Exception:
                    pass

            if pager:
                total_pages = pager.pagecount if total > 0 else 1
                pager.results.fragmenter = highlight.ContextFragmenter(maxchars=200, surround=50)
                pager.results.formatter  = highlight.HtmlFormatter(tagname="mark", classname="hl")

                for r in pager:
                    titre = r["titre"]
                    if doc_type:
                        _, ext = os.path.splitext(titre)
                        if ext.lower() != doc_type:
                            continue

                    snippet_raw = r.highlights("contenu")
                    snippet_html = Markup(snippet_raw) if snippet_raw else escape(r["contenu"][:300])

                    results_list.append({
                        "titre":             titre,
                        "contenu_highlight": snippet_html,
                        "score":             round(r.score, 2),
                    })

    return render_template(
        "results.html",
        query=query_str,
        results=results_list,
        field=field,
        doc_type=doc_type,
        page=page,
        total=total,
        total_pages=total_pages,
        per_page=per_page,
        used_fuzzy=used_fuzzy,
        sort_by=sort_by,
    )


@app.route("/view/<path:filename>")
def view(filename):
    safe_name = secure_filename(filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        path = os.path.join(UPLOAD_FOLDER, safe_name)
        
    if not os.path.exists(path):
        flash(f"⚠ Fichier introuvable : {filename}", "error")
        return redirect(request.referrer or url_for("home"))

    return send_from_directory(UPLOAD_FOLDER, os.path.basename(path))


@app.route("/delete/<path:filename>", methods=["POST"])
def delete(filename):
    deleted_index = False
    deleted_file  = False

    try:
        writer = ix.writer()
        writer.delete_by_term("id", filename)
        writer.commit()
        deleted_index = True
        
        # ✅ نحذفو من الـ RAG زادة
        rag.delete_document_from_vector_db(filename)
    except:
        pass

    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
            deleted_file = True
        except:
            pass

    if deleted_index or deleted_file:
        flash(f"🗑 '{filename}' a été supprimé.", "success")
    else:
        flash(f"⚠ Impossible de supprimer '{filename}'.", "error")

    return redirect(request.referrer or url_for("home"))


@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for("home"))

    indexed = []
    skipped = []

    for f in files:
        if not f.filename:
            continue

        original_filename = f.filename
        safe_name = secure_filename(original_filename)

        if not safe_name:
            skipped.append(original_filename)
            continue

        _, ext = os.path.splitext(safe_name)
        if ext.lower() not in ALLOWED_EXT:
            skipped.append(original_filename)
            continue

        save_path = os.path.join(UPLOAD_FOLDER, original_filename)

        try:
            f.save(save_path)
        except Exception as e:
            skipped.append(original_filename)
            continue

        if index_file(save_path, original_filename):
            indexed.append(original_filename)
        else:
            skipped.append(original_filename)

    if indexed:
        flash(f"{len(indexed)} fichier(s) importé(s) : {', '.join(indexed)}", "success")
    if skipped:
        flash(f"{len(skipped)} fichier(s) ignoré(s).", "error")

    return redirect(url_for("home"))


@app.errorhandler(413)
def too_large(e):
    flash("Fichier trop volumineux (max 50 Mo).", "error")
    return redirect(url_for("home")), 302


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)