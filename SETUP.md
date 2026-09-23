# EvidenceFlow AI - Setup Guide

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Required: Groq API Key for LLM
GROQ_API_KEY=your_groq_api_key_here

# Optional: Cohere API Key for reranking
# If not provided, reranking will use a fallback method
COHERE_API_KEY=your_cohere_api_key_here
```

### Getting API Keys

1. **Groq API Key**: Sign up at https://groq.com/ and get your API key from the dashboard
2. **Cohere API Key**: Sign up at https://cohere.com/ and get your API key from the dashboard (optional)

## Installation

1. Install dependencies using uv:
```bash
uv sync
```

Or using pip:
```bash
pip install -r requirement.txt
```

## Running the Application

### Streamlit UI (Recommended)

```bash
streamlit run evidenceflow_app.py
```

### Command Line Evaluation

```bash
python run_evaluation.py
```

### Original Basic RAG (Legacy)

```bash
python main.py
```

## Document Preparation

Place your PDF documents in the `./data` directory. The system will automatically:
- Load all PDF files
- Chunk them into manageable pieces
- Create embeddings
- Build BM25 and vector indexes

## Features

- **Hybrid Retrieval**: Combines BM25 keyword search with vector similarity
- **Agentic Loop**: Intelligently rewrites queries when evidence is insufficient
- **Reranking**: Improves result relevance using Cohere API (or fallback)
- **Evidence Grading**: Evaluates quality, relevance, coverage, and diversity
- **Citation Verification**: Ensures claims are supported by evidence
- **Cache-Augmented Generation**: Semantic caching for faster responses
- **Confidence Scoring**: Overall confidence based on multiple factors
- **Evaluation Mode**: Comprehensive testing and metrics

## Architecture

```
Documents → Ingestion → Chunking → BM25 Index → Vector Index
                                                ↓
Query → Understanding → Hybrid Retrieval → Reranking → Evidence Grading
                                                ↓
                                    Agentic Loop (if needed)
                                                ↓
                                    Answer Generation → Citation Verification
                                                ↓
                                    CAG Cache → Final Grounded Answer
```

## Modular Design

The system is designed to be modular and extensible:

- **PostgreSQL/pgvector**: Can replace ChromaDB for production
- **Elasticsearch/OpenSearch**: Can replace BM25 for production
- **Redis**: Can enhance caching for production
- **Production LLM APIs**: Easy to swap Groq for other providers

## Evaluation Metrics

The evaluation system measures:
- Retrieval Recall
- Precision
- Answer correctness
- Citation accuracy
- Cache hit rate
- Latency
- Evidence quality (relevance, coverage, diversity)
- Confidence scores
