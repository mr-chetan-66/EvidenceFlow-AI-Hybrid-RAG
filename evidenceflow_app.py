"""
EvidenceFlow AI - Advanced Enterprise Knowledge System
Agentic RAG with hybrid retrieval, reranking, evidence grading, citation verification, and CAG
"""
import streamlit as st
import time
from pathlib import Path
from typing import Dict, Any, List

# Lazy imports for faster initial loading - only import when needed
import sys
import importlib

def get_module(module_name, class_name=None):
    """Lazy import function"""
    try:
        module = importlib.import_module(module_name)
        if class_name:
            return getattr(module, class_name)
        return module
    except ImportError:
        return None


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EvidenceFlow AI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown("""
<style>
    .main-title {
        font-size: 32px;
        font-weight: 600;
        text-align: center;
        margin-bottom: 20px;
        color: #1a1a1a;
    }
    
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def init_session_state():
    """Initialize session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'system_ready' not in st.session_state:
        st.session_state.system_ready = False
    
    if 'hybrid_retriever' not in st.session_state:
        st.session_state.hybrid_retriever = None
    
    if 'agentic_retrieval' not in st.session_state:
        st.session_state.agentic_retrieval = None
    
    if 'cache' not in st.session_state:
        st.session_state.cache = None
    
    if 'retrieval_history' not in st.session_state:
        st.session_state.retrieval_history = []
    
    if 'current_mode' not in st.session_state:
        st.session_state.current_mode = 'chat'


init_session_state()


# ============================================================
# CACHED RESOURCES
# ============================================================

@st.cache_resource
def get_embedding_manager():
    """Get cached embedding manager"""
    EmbeddingManager = get_module('src.embedding', 'EmbeddingManager')
    with st.spinner("Loading embedding model..."):
        return EmbeddingManager()


@st.cache_resource
def get_vectorstore():
    """Get cached vector store"""
    VectorStore = get_module('src.vectorstore', 'VectorStore')
    with st.spinner("Initializing vector store..."):
        return VectorStore()


@st.cache_resource
def get_cache(embedding_manager):
    """Get cached CAG cache"""
    CAGCache = get_module('src.cag_cache', 'CAGCache')
    return CAGCache(embedding_manager=embedding_manager)


# ============================================================
# SYSTEM INITIALIZATION
# ============================================================

def initialize_system():
    """Initialize the EvidenceFlow AI system - optimized for speed with persistence check"""
    with st.status("🚀 Setting up your knowledge base...", expanded=True) as status:
        try:
            # Lazy import modules
            process_all_pdfs = get_module('src.load_and_chunk', 'process_all_pdfs')
            chunk_documnents = get_module('src.load_and_chunk', 'chunk_documnents')
            HybridRetriever = get_module('src.hybrid_retrieval', 'HybridRetriever')
            AgenticRetrieval = get_module('src.agentic_retrieval', 'AgenticRetrieval')
            
            # Check if vector store already has data
            status.write("🔍 Checking existing data...")
            vectorstore = get_vectorstore()
            if vectorstore.collection.count() > 0:
                status.write("✅ Found existing vector store data")
                status.write("🔄 Loading from cache...")
                
                # Initialize components without reprocessing
                embedding_manager = get_embedding_manager()
                
                # Initialize retrievers with existing data
                hybrid_retriever = HybridRetriever(embedding_manager, vectorstore)
                # Try to load existing texts to rebuild BM25 index
                try:
                    existing_data = vectorstore.collection.get(limit=100)
                    if existing_data and 'documents' in existing_data:
                        texts = existing_data['documents']
                        hybrid_retriever.index_documents(texts)
                except:
                    pass  # Fallback - will work with vector search only
                
                agentic_retrieval = AgenticRetrieval(hybrid_retriever, max_iterations=2, enable_reranking=True, enable_citation_check=False)
                cache = get_cache(embedding_manager)
                
                st.session_state.hybrid_retriever = hybrid_retriever
                st.session_state.agentic_retrieval = agentic_retrieval
                st.session_state.cache = cache
                st.session_state.system_ready = True
                
                status.update(label="✅ System ready from cache!", state="complete")
                return True
            
            # Step 1: Load documents from PDF folder specifically
            status.write("📄 Loading PDF documents...")
            all_documents = process_all_pdfs("./data/pdf")
            
            # Limit documents for faster processing
            if len(all_documents) > 500:
                status.write(f"⚡ Limiting to first 500 pages for faster processing")
                all_documents = all_documents[:500]
            
            status.write(f"✅ Loaded {len(all_documents)} document pages")
            
            # Step 2: Chunk documents
            status.write("✂️ Processing chunks...")
            all_chunks = chunk_documnents(all_documents)
            status.write(f"✅ Created {len(all_chunks)} chunks")
            
            # Step 3: Initialize AI components (cached)
            status.write("🧠 Loading AI models...")
            embedding_manager = get_embedding_manager()
            status.write("✅ AI models loaded")
            
            # Step 4: Generate embeddings
            status.write("🔢 Generating embeddings (this may take a moment)...")
            texts = [doc.page_content for doc in all_chunks]
            embeddings = embedding_manager.genetate_embedding(texts)
            status.write("✅ Embeddings generated")
            
            # Step 5: Store in vector store
            status.write("💾 Building search index...")
            vectorstore.add_documents(all_chunks, embeddings)
            status.write("✅ Search index ready")
            
            # Step 6: Initialize retrievers
            status.write("🔗 Connecting retrieval systems...")
            hybrid_retriever = HybridRetriever(embedding_manager, vectorstore)
            hybrid_retriever.index_documents(texts)
            agentic_retrieval = AgenticRetrieval(hybrid_retrieval, max_iterations=2, enable_reranking=True, enable_citation_check=False)
            cache = get_cache(embedding_manager)
            status.write("✅ Retrieval systems connected")
            
            # Store in session state
            st.session_state.hybrid_retriever = hybrid_retriever
            st.session_state.agentic_retrieval = agentic_retrieval
            st.session_state.cache = cache
            st.session_state.system_ready = True
            
            status.update(label="✅ System ready!", state="complete")
            return True
            
        except Exception as e:
            status.update(label=f"❌ Setup failed: {str(e)}", state="error")
            st.error(f"Setup failed: {e}")
            return False

if __name__ == "__main__":
    main()
