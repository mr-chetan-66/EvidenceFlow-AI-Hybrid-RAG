from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

## CONVERTING PDF TO DOCUMENTS
def process_all_pdfs(pdf_directory):
    all_documents = []
    pdf_dir = Path(pdf_directory)
    print(f"Looking for PDFs in: {pdf_dir}")
    print(f"Directory exists: {pdf_dir.exists()}")
    
    pdf_files = [path for path in pdf_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf"]
    print(f"Found {len(pdf_files)} PDF files")
    
    for pdf_file in pdf_files:
        print(f"Processing: {pdf_file}")
        try:
            all_documents.extend(process_pdf(pdf_file))
        except Exception as e:
            print(f"  ✗ Error loading {pdf_file.name}: {e}")

    print(f"\nTotal documents loaded: {len(all_documents)}")
    return all_documents


def process_pdf(pdf_path):
    """Load one PDF and preserve the source and page metadata used by retrieval."""
    pdf_file = Path(pdf_path)
    documents = PyMuPDFLoader(str(pdf_file)).load()
    print(f"  Loaded {len(documents)} pages from {pdf_file.name}")
    for doc in documents:
        doc.metadata.update({
            "source": str(pdf_file),
            "file_type": "pdf",
            "page": doc.metadata.get("page", 0),
        })
    return documents

def chunk_documnents(documents, chunk_size=300, chunk_overlap=50):
    """Ultra-optimized chunking with very small chunks for maximum speed"""
    text_splitter=RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n","\n"," ",""]
    )
    
    all_chunks=text_splitter.split_documents(documents)
    
    # Ensure metadata is preserved during chunking - LangChain preserves this automatically
    # But let's double-check and fix any missing page numbers
    for chunk in all_chunks:
        if 'page' not in chunk.metadata or chunk.metadata['page'] is None:
            chunk.metadata['page'] = 'N/A'
    
    print(f"Split {len(documents)} documents into {len(all_chunks)} chunks")
    return all_chunks

