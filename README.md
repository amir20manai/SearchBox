\# SearchBox – Intelligent Document Search Engine



An intelligent document search engine that combines \*\*full-text search\*\*, \*\*semantic search\*\*, and \*\*AI-powered document conversations\*\* in one web application.



SearchBox allows users to upload documents, search their content, retrieve relevant information, and ask questions about their documents using Retrieval-Augmented Generation (RAG).



\## ✨ Features



\### 1. Document Management

\- Upload multiple documents.

\- Support for PDF, DOCX, and TXT files.

\- View uploaded documents.

\- Delete documents.

\- Display document statistics and file information.



\### 2. Advanced Full-Text Search

\- Search by document title or content.

\- Fuzzy search for approximate word matching.

\- Highlight matching keywords in search results.

\- Filter documents by file type.

\- Sort results by relevance, name, or modification date.

\- Paginated search results.



\### 3. Semantic Search \& Vector Database

\- Generate multilingual text embeddings.

\- Split documents into smaller text chunks.

\- Store document embeddings in ChromaDB.

\- Retrieve relevant document sections using semantic similarity.



\### 4. AI-Powered Chat with Documents

\- Ask questions about uploaded documents.

\- Generate answers using the RAG architecture.

\- Retrieve relevant document context before generating answers.

\- Display document sources used for answers.

\- Respond in the same language as the user's question.

\- Select a specific document or search across all documents.



\### 5. Data Export

\- Export document information to CSV.

\- Include file names, types, sizes, and modification dates.



\## 🛠️ Technologies Used



| Technology | Purpose |

|---|---|

| Python | Backend development |

| Flask | Web framework |

| Whoosh | Full-text search engine |

| ChromaDB | Vector database |

| Sentence Transformers | Multilingual text embeddings |

| Groq API | AI-powered answer generation |

| PyPDF2 | PDF text extraction |

| python-docx | Word document processing |

| HTML / CSS / JavaScript | Frontend development |



\## 🧠 System Architecture



SearchBox combines two complementary search approaches:



\*\*1. Full-Text Search\*\*



Whoosh indexes document titles and contents, enabling keyword-based search, fuzzy matching, filtering, sorting, and highlighting.



\*\*2. Semantic Search with RAG\*\*



The RAG pipeline:

1\. Extracts text from uploaded documents.

2\. Splits text into smaller chunks.

3\. Converts chunks into vector embeddings.

4\. Stores embeddings in ChromaDB.

5\. Converts user questions into embeddings.

6\. Retrieves the five most relevant chunks.

7\. Sends the retrieved context to the Groq API.

8\. Returns an AI-generated answer with its document sources.



\## 📁 Project Structure



```text

SearchBox/

│

├── app.py

├── indexer.py

├── build\_vectors.py

├── rag.py

├── requirements.txt

├── .env.example

├── .gitignore

│

├── templates/

│   ├── index.html

│   ├── results.html

│   └── chat.html

│

├── documents/       # Local uploaded documents

├── indexdir/        # Whoosh index (generated)

└── chroma\_db/       # ChromaDB storage (generated)

```



\## ⚙️ Installation \& Setup



\### Prerequisites

\- Python 3.10 or later (use a version compatible with the installed dependencies).

\- A Groq API key.



\### 1. Clone the repository



```bash

git clone https://github.com/amir20manai/SearchBox.git

cd SearchBox

```



\### 2. Create a virtual environment



```bash

python -m venv venv

```



Activate it on Windows:



```bash

venv\\Scripts\\activate

```



\### 3. Install dependencies



```bash

pip install -r requirements.txt

```



\### 4. Configure environment variables



Create a `.env` file in the project root:



```env

GROQ\_API\_KEY=your\_groq\_api\_key

```



Replace `your\_groq\_api\_key` with your own API key.



\### 5. Run the application



```bash

python app.py

```



Open your browser at:



```text

http://127.0.0.1:5000

```



\## 📚 Document Indexing



SearchBox uses two indexing processes:



\- \*\*Whoosh indexing:\*\* Run `python indexer.py` to index existing documents for full-text search.

\- \*\*Vector indexing:\*\* Run `python build\_vectors.py` to generate embeddings and populate ChromaDB for semantic search.



New documents uploaded through the application are indexed automatically.



\## 🔐 Security



\- Keep API keys in environment variables.

\- Never commit `.env` or private documents.

\- Do not expose personal documents or generated database files in the public repository.



\## 🚀 Future Improvements



\- Voice-based document search.

\- Advanced search filters.

\- Search history and saved queries.

\- More document formats.

\- Improved document preview.

\- Enhanced user interface.

\- More advanced RAG capabilities.



\## 👨‍💻 Author



\*\*Amir Manai\*\*



GitHub: \[@amir20manai](https://github.com/amir20manai)



\---



\*SearchBox – Search smarter. Understand better.\*

