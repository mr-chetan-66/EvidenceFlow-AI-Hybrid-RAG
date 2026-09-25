import numpy as np
import chromadb
import hashlib
import os
from pathlib import Path
from typing import List,Any

class VectorStore:
    def __init__(self, collection_name:str="pdf_documents",persist_directory:str|None=None):
        self.collection_name=collection_name
        if persist_directory is None:
            project_root = Path(__file__).resolve().parents[1]
            # Check if running on Render (has mounted disk)
            render_disk_path = os.getenv("RENDER_DISK_PATH", "/opt/render/project/data")
            if os.path.exists(render_disk_path):
                persist_directory = str(Path(render_disk_path) / "vector_store")
            else:
                persist_directory = str(project_root / "data" / "vector_store")
        self.persist_directory=persist_directory
        
        os.makedirs(self.persist_directory,exist_ok=True)
        
        self.client=chromadb.PersistentClient(path=self.persist_directory)
        self.collection=self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "description":"PDF documents RAG vector"
            }
        )
        
    def add_documents(self,all_chunks:List[Any],embedd:np.ndarray):
        
        if not all_chunks:
            print("No record to upload")
            return
        
        if len(all_chunks)!=len(embedd):
            raise ValueError("Chunk and Embedd size doesnt match")
        
        
        ids=[]
        metadatas=[]
        embeddings=[]
        documents=[]
        
        for index,(chk,ebd) in enumerate(zip(all_chunks,embedd)):
            
            source=chk.metadata.get("source","unknown")
            page=chk.metadata.get("page",0)
            
            unique_string=f"{source}|{page}|{index}|{chk.page_content}"
            
            doc_id=hashlib.sha256(unique_string.encode('utf-8')).hexdigest()
            
            ids.append(doc_id)
            documents.append(chk.page_content)
            metadata=dict(chk.metadata)
            metadatas.append(metadata)
            embeddings.append(ebd.tolist())
            
        BATCH_SIZE=500
        for s in range(0,len(ids),BATCH_SIZE):
            e=s+BATCH_SIZE
            self.collection.upsert(
                ids=ids[s:e],
                documents=documents[s:e],
                metadatas=metadatas[s:e],
                embeddings=embeddings[s:e]
            )

        print(f"Total chunks {self.collection.count()} Stored")
        
    def similar_search(self,query_embedding:np.ndarray,n_results=5):
        result=self.collection.query(query_embeddings=[query_embedding.tolist()],n_results=n_results)
        # Ensure distances are included in the result
        if 'distances' not in result and 'documents' in result:
            # If distances not returned, create dummy distances
            result['distances'] = [[1.0] * len(result['documents'][0])]
        return result