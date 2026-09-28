# EvidenceFlow AI

An advanced agentic enterprise knowledge system that intelligently retrieves, evaluates, verifies, and reuses knowledge from document collections.

## 🎯 Features

### Core Capabilities
- **Hybrid Retrieval**: Combines BM25 keyword search with vector similarity search for optimal results
- **Agentic Retrieval Loop**: Intelligently rewrites queries when evidence is insufficient
- **Reranking**: Improves evidence relevance using Cohere API (with fallback)
- **Evidence Grading**: Evaluates quality, relevance, coverage, and diversity of retrieved evidence
- **Citation Verification**: Ensures generated claims are supported by retrieved evidence
- **Cache-Augmented Generation (CAG)**: Semantic caching for frequently asked questions
- **Confidence Scoring**: Multi-factor confidence assessment based on retrieval quality and citation verification

### User Interface
- **Document Upload**: Easy PDF document ingestion
- **Search/Chat Interface**: Natural language query interface
- **Retrieval Details**: BM25 vs vector retrieval information
- **Reranking Results**: View reranked evidence with scores
- **Generated Answers**: Grounded responses with citations
- **Confidence Metrics**: Real-time confidence scoring
- **Cache Status**: Monitor cache hit/miss rates
- **Retrieval History**: Track query rewriting iterations

### Evaluation Mode
- **Retrieval Recall & Precision**: Measure retrieval effectiveness
- **Answer Correctness**: Evaluate generated response quality
- **Citation Accuracy**: Verify claim support
- **Cache Hit Rate**: Monitor caching efficiency
- **Latency Tracking**: Performance metrics
- **Visual Analytics**: Charts and graphs for performance analysis

## 🏗️ Architecture

```
Documents → Document Ingestion → Chunking + Metadata
                                                ↓
                 BM25 Index ← Chunking → Vector Index
                                                ↓
                   Hybrid Retrieval (BM25 + Vector)
                                                ↓
                         Reranking
                                                ↓
                    Evidence Grading
                                                ↓
            Agentic Loop (Query Rewriting if needed)
                                                ↓
                  LLM Answer Generation
                                                ↓
                  Citation Verification
                                                ↓
                  CAG/Cache Check
                                                ↓
            Final Grounded Answer with Citations
```

## 🚀 Quick Start

### Prerequisites
- Python 3.14+
- Node.js 18+ and npm (required for the React frontend)
- `uv` (recommended) or `pip`
- Groq API key (required)
- Cohere API key (optional, for reranking)

### 1. Install Python dependencies

From the project root:

```bash
uv sync
```

If you are not using `uv`, create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
python -m pip install -r requirement.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_groq_api_key_here
COHERE_API_KEY=your_cohere_api_key_here  # Optional
GOOGLE_CLIENT_ID=your_google_client_id_here  # Optional - for Google OAuth
GOOGLE_CLIENT_SECRET=your_google_client_secret_here  # Optional - for Google OAuth
```

Copy the values from `ENV_EXAMPLE.txt` if needed. Add PDF documents to `data/pdf/` before initializing the system.

**Google OAuth Setup (Optional):**
To enable Google OAuth login:
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to Credentials → Create Credentials → OAuth client ID
5. Application type: Web application
6. Authorized redirect URIs: `http://localhost:8001/auth/google/callback`
7. Copy Client ID and Client Secret to your `.env` file
8. Restart the backend server to enable Google login

### 3. Run the application

The recommended architecture uses a FastAPI backend and React frontend. Start each service in a separate terminal from the project root.

**Terminal 1: FastAPI backend**
```bash
python -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8001
```

**Terminal 2: React frontend**
```bash
cd frontend
npm install
npm run dev
```

Open the application at [http://localhost:3000](http://localhost:3000). The backend API and interactive documentation are available at [http://localhost:8001](http://localhost:8001) and [http://localhost:8001/docs](http://localhost:8001/docs).

The frontend defaults to `http://localhost:8001` for the API. To use another backend URL, create `frontend/.env` with:

```bash
VITE_API_URL=http://localhost:8001
```

**Streamlit alternative:**

To run the combined legacy Streamlit application instead of the React/FastAPI architecture:

```bash
streamlit run evidenceflow_app.py
```

**Default Login Credentials:**
- Admin: `admin@evidenceflow.ai` / `admin123`
- The admin user is auto-created on first startup

## 📖 Usage

### Chat Mode
1. Initialize the system using the sidebar
2. Ask questions about your documents
3. View detailed retrieval metrics and evidence quality
4. Check citation verification for each response

### Evaluation Mode
1. Switch to Evaluation mode in the sidebar
2. Enter test questions (one per line)
3. Run evaluation to see comprehensive metrics
4. Review visualizations and detailed results

### Command Line Evaluation
```bash
python run_evaluation.py
```

## 🔧 Modular Design

The system is designed for easy extension to production infrastructure:

- **ChromaDB** → PostgreSQL/pgvector
- **BM25** → Elasticsearch/OpenSearch  
- **File-based Cache** → Redis
- **Groq** → Production LLM APIs (OpenAI, Anthropic, etc.)

## 📊 Evaluation Metrics

The system tracks and measures:
- Retrieval Recall & Precision
- Answer Correctness
- Citation Accuracy
- Cache Hit Rate
- Latency
- Evidence Quality (relevance, coverage, diversity)
- Confidence Scores

## 🛠️ Technical Stack

- **Framework**: Streamlit (UI), LangChain (orchestration)
- **Vector Store**: ChromaDB
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-V2)
- **Retrieval**: BM25 + Vector Search (Hybrid)
- **Reranking**: Cohere API
- **LLM**: Groq (GPT-OSS-20B)
- **Caching**: Semantic caching with embeddings

## 📝 Project Structure

```
RAGApplication/
├── src/
│   ├── load_and_chunk.py      # Document ingestion and chunking
│   ├── embedding.py           # Embedding generation
│   ├── vectorstore.py         # Vector database management
│   ├── bm25_search.py         # BM25 keyword search
│   ├── hybrid_retrieval.py    # Hybrid BM25 + vector retrieval
│   ├── reranker.py            # Document reranking
│   ├── evidence_grader.py     # Evidence quality evaluation
│   ├── citation_verifier.py   # Citation verification
│   ├── cag_cache.py           # Cache-Augmented Generation
│   ├── agentic_retrieval.py   # Agentic retrieval loop
│   └── evaluation.py          # Evaluation system
├── data/                      # Document storage
├── evidenceflow_app.py        # Main Streamlit application
├── run_evaluation.py          # Command-line evaluation
├── app.py                     # Legacy basic RAG app
├── main.py                    # Legacy CLI interface
└── SETUP.md                   # Detailed setup guide
```

## 🤝 Contributing

This is an MVP designed for local deployment with modular architecture for production scaling.

## 📄 License

See LICENSE file for details.

## 🙏 Acknowledgments

Built with:
- LangChain
- Streamlit
- ChromaDB
- Sentence Transformers
- Groq
- Cohere