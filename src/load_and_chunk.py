from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

## CONVERTING PDF TO DOCUMENTS
def process_all_pdfs(pdf_directory):
    all_documents = []
    pdf_dir = Path(pdf_directory)
    pdf_files = list(pdf_dir.rglob("*.pdf"))
    for pdf_file in pdf_files:
        try:
            documents = PyMuPDFLoader(str(pdf_file)).load()
            for doc in documents:
                doc.metadata.update({
                    "source": str(pdf_file),
                    "file_type": "pdf"
                })
            all_documents.extend(documents)
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\nTotal documents loaded: {len(all_documents)}")
    return all_documents

def chunk_documnents(documents, chunk_size=1000, chunk_overlap=200):
    text_splitter=RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len, # len to count character we can haev custom fuction for this
        separators=["\n\n","\n"," ",""] # can add '.' bcz mr. or 6.2
    )
    
    all_chunks=text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(all_chunks)} chunks")
    return all_chunks

