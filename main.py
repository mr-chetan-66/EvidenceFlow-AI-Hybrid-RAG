from src.load_and_chunk import process_all_pdfs,chunk_documnents
from src.embedding import EmbeddingManager
from src.vectorstore import VectorStore

def trainRAG(embedding_manager:EmbeddingManager,vectorstore:VectorStore):
    all_documents=process_all_pdfs("./data")
    all_chunks=chunk_documnents(all_documents)
    texts=[doc.page_content for doc in all_chunks]
    if not texts:
        print("No text found.")
        return
    
    all_embedding=embedding_manager.genetate_embedding(texts)
    print("Embedding Done")
    vectorstore.add_documents(all_chunks,all_embedding)
    
def retrive():
    from src.search import RagBot
    print("\nRagBot (¬‿¬) Here - What do you want to know? EXIT = :(")
    while True:
        query=input("\n YOU ==> ")
        if query==':(': return
        print(f"\n (¬‿¬) ==> what {RagBot(query)}")
    

if __name__=="__main__":
    print("\nWhat do want to do:\n1.Train RAG\n2.Search\n")
    todo=int(input())
    
    if todo==1:
        print("Training RAG...\n")
        embedding_manager=EmbeddingManager()
        vectorstore=VectorStore()
        trainRAG(embedding_manager,vectorstore)
        print("Done\n")
        retrive()
    elif todo==2:
        retrive()
    else:
        print("Invalid option.")
        
            