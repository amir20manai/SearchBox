import os
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv

# ✅ نقراو الـ API Key من ملف .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ✅ نجهزو الموديل إلّي يحول الكلمات لأرقام (Vectors) - Multilingual (يفهم 50 لغة)
print("⏳ Chargement du modèle d'embedding (peut prendre 10 secondes)...")
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# ✅ نجهزو ChromaDB (قاعدة البيانات)
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="documents_collection")

# ✅ نجهزو الـ Groq (الـ AI)
if GROQ_API_KEY:
    ai_client = Groq(api_key=GROQ_API_KEY)
else:
    ai_client = None
    print("⚠️ Attention : GROQ_API_KEY n'est pas défini dans le fichier .env")


def chunk_text(text, chunk_size=500, overlap=50):
    """تقسيم النص لمقاطع صغيرة (Chunks) باش الـ AI ينجّم يقراهم."""
    chunks = []
    words = text.split()
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
            
    return chunks


def add_document_to_vector_db(filename, text):
    """ناخذو النص، نقسمو، و نحطوه في ChromaDB مع الـ Vectors متاعو."""
    if not text.strip():
        return False

    try:
        chunks = chunk_text(text)
        
        # باش ما نعملوش doublons، نمسحو القديم إذا موجود
        try:
            collection.delete(where={"source": filename})
        except:
            pass

        # نحولو المقاطع لأرقام
        embeddings = embedder.encode(chunks).tolist()
        
        # نجهزو الـ IDs و الـ Metadata
        ids = [f"{filename}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename} for _ in range(len(chunks))]
        
        # نحطوهم في القاعدة
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        return True
    except Exception as e:
        print(f"❌ Erreur dans add_document_to_vector_db: {e}")
        return False


def delete_document_from_vector_db(filename):
    """حذف الملف من الـ Vector DB كي المستخدم يحذفو من الموقع."""
    try:
        collection.delete(where={"source": filename})
        return True
    except Exception as e:
        print(f"❌ Erreur dans delete_document_from_vector_db: {e}")
        return False


def ask_documents(question, filename=None):
    """الدالة الأساسية: تاخذ سؤال، تلقى المقاطع، و تسأل الـ AI."""
    if not ai_client:
        return "⚠️ Erreur : Clé API Groq manquante. Vérifiez le fichier .env."

    # 1. نحولو السؤال لـ Vector
    question_embedding = embedder.encode([question]).tolist()

    # 2. نلقاو أقرب 5 مقاطع
    where_clause = {"source": filename} if filename else None
    
    try:
        results = collection.query(
            query_embeddings=question_embedding,
            n_results=5,
            where=where_clause
        )
    except Exception as e:
        return f"Erreur lors de la recherche dans les documents : {e}"

    # 3. نجمعو النصوص إلّي لقيناهم
    documents = results['documents'][0] if results['documents'] else []
    metadatas = results['metadatas'][0] if results['metadatas'] else []

    if not documents:
        return "Je n'ai trouvé aucune information pertinente dans les documents pour répondre à votre question."

    context = "\n\n---\n\n".join(documents)
    
    # نجمعو المصادر (باش نعرضوهم للمستخدم)
    sources = list(set([m['source'] for m in metadatas]))

    # 4. نسألو الـ AI
    # ✅ الـ Prompt الجديد (مؤكد على اللغة)
    system_prompt = """Tu es un assistant intelligent. Réponds à la question de l'utilisateur en te basant UNIQUEMENT sur le contexte fourni ci-dessous.
CRITICAL RULE: You MUST reply in the SAME LANGUAGE as the user's question. 
- If the question is in English, reply in English.
- If the question is in Arabic, reply in Arabic.
- If the question is in French, reply in French.
Si la réponse ne se trouve pas dans le contexte, dis clairement que l'information n'est pas présente dans les documents. Ne jamais inventer des informations."""

    # ✅ زدنا التأكيد على اللغة هنا (في الـ User Prompt مباشرة)
    user_prompt = f"""Contexte:
{context}

Question: {question}

⚠️ IMPORTANT: Réponds à la question ci-dessus EXACTEMENT dans la même langue que la question (if the question is in English, answer in English; if it's in Arabic, answer in Arabic; if it's in French, answer in French). Do NOT translate the answer."""

    try:
        chat_completion = ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-oss-20b",
            temperature=0.1, # ✅ نقصنا الـ Temperature (باش يكون دقيق و ما يخترعش)
        )
        answer = chat_completion.choices[0].message.content
    except Exception as e:
        return f"Erreur avec l'API de l'IA : {e}"

    return {"answer": answer, "sources": sources}