import numpy as np
import chromadb
import hashlib
import os
from pathlib import Path
from typing import List,Any
from src.storage_paths import get_data_root

class VectorStore:
    def __init__(self, collection_name:str="pdf_documents",persist_directory:str|None=None):
        self.collection_name=collection_name
        if persist_directory is None:
            persist_directory = str(get_data_root() / "vector_store")
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
        return ids

    def replace_documents(self, all_chunks: List[Any], embeddings: np.ndarray):
        """Upsert chunks and remove stale chunks for only their source files."""
        if not all_chunks:
            return []

        document_ids = self.add_documents(all_chunks, embeddings)
        retained_ids = set(document_ids)
        sources = {
            chunk.metadata.get("source")
            for chunk in all_chunks
            if chunk.metadata.get("source")
        }

        for source in sources:
            stored = self.collection.get(
                where={"source": source},
                include=["metadatas"],
            )
            stale_ids = [
                document_id
                for document_id in stored.get("ids", [])
                if document_id not in retained_ids
            ]
            if stale_ids:
                self.collection.delete(ids=stale_ids)

        return document_ids

    def get_all_documents(self, batch_size: int = 1000):
        """Read the complete persistent text corpus and its citation metadata in pages."""
        documents = []
        metadatas = []
        document_ids = []
        total_count = self.collection.count()

        for offset in range(0, total_count, batch_size):
            batch = self.collection.get(
                limit=min(batch_size, total_count - offset),
                offset=offset,
                include=["documents", "metadatas"],
            )
            batch_documents = batch.get("documents") or []
            if not batch_documents:
                break
            documents.extend(batch_documents)
            metadatas.extend(batch.get("metadatas") or [{} for _ in batch_documents])
            document_ids.extend(batch.get("ids") or [None for _ in batch_documents])

        return documents, metadatas, document_ids
        
    def similar_search(self,query_embedding:np.ndarray,n_results=5):
        result=self.collection.query(query_embeddings=[query_embedding.tolist()],n_results=n_results)
        # Ensure distances are included in the result
        if 'distances' not in result and 'documents' in result:
            # If distances not returned, create dummy distances
            result['distances'] = [[1.0] * len(result['documents'][0])]
        return result