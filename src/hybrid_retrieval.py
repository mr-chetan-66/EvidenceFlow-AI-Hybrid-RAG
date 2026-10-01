"""
Hybrid Retrieval Module
Combines BM25 keyword search and vector similarity search
"""
from typing import List, Dict, Any, Tuple
import numpy as np
from src.bm25_search import BM25Search
from src.embedding import EmbeddingManager
from src.vectorstore import VectorStore


class HybridRetriever:
    MIN_RELEVANCE_SCORE = 0.12

    def __init__(self, embedding_manager: EmbeddingManager, vectorstore: VectorStore):
        """
        Initialize hybrid retriever
        
        Args:
            embedding_manager: EmbeddingManager instance
            vectorstore: VectorStore instance
        """
        self.embedding_manager = embedding_manager
        self.vectorstore = vectorstore
        self.bm25 = BM25Search()
        self.is_indexed = False
        
    def index_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        document_ids: List[str] = None,
    ):
        """
        Index documents for both BM25 and vector search
        
        Args:
            documents: List of document strings
        """
        # Index for BM25
        self.bm25.index_documents(documents, metadatas, document_ids)
        self.is_indexed = self.bm25.is_indexed()
        
    def retrieve(
        self, 
        query: str, 
        k: int = 10, 
        alpha: float = 0.65
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Hybrid retrieval combining BM25 and vector search
        
        Args:
            query: Search query
            k: Number of results to return
            alpha: Weight for combining scores (0-1)
                   0 = BM25 only, 1 = vector only, 0.5 = equal weight
            
        Returns:
            Tuple of (results, metadata)
            results: List of retrieved documents with combined scores
            metadata: Dictionary with retrieval statistics
        """
        if not self.is_indexed:
            raise ValueError("Documents not indexed. Call index_documents first.")
            
        alpha = min(max(alpha, 0.0), 1.0)

        # BM25 retrieval
        bm25_results = self.bm25.search(query, k=k)
        
        # Vector retrieval
        query_embedding = self.embedding_manager.genetate_embedding([query])[0]
        vector_results = self.vectorstore.similar_search(query_embedding, n_results=k)
        
        # Convert vector results to standard format
        vector_docs = vector_results['documents'][0]
        vector_scores = vector_results['distances'][0] if 'distances' in vector_results else [1.0] * len(vector_docs)
        vector_metadata = vector_results['metadatas'][0] if 'metadatas' in vector_results else [{}] * len(vector_docs)
        vector_ids = vector_results.get('ids', [[]])[0]
        
        # Normalize and combine scores
        combined_results = self._combine_results(
            bm25_results, 
            vector_docs, 
            vector_scores, 
            vector_metadata,
            vector_ids,
            alpha
        )
        combined_results = combined_results[:k]
        
        # Prepare metadata
        retrieval_metadata = {
            'bm25_count': len(bm25_results),
            'vector_count': len(vector_docs),
            'bm25_corpus_count': len(self.bm25.documents),
            'alpha': alpha,
            'query': query
        }
        
        return combined_results, retrieval_metadata
    
    def _combine_results(
        self,
        bm25_results: List[Dict[str, Any]],
        vector_docs: List[str],
        vector_scores: List[float],
        vector_metadata: List[Dict[str, Any]],
        vector_ids: List[str],
        alpha: float
    ) -> List[Dict[str, Any]]:
        """
        Combine BM25 and vector search results
        
        Args:
            bm25_results: BM25 search results
            vector_docs: Vector search documents
            vector_scores: Vector search scores (distances)
            vector_metadata: Vector search metadata
            alpha: Weight for combining scores
            
        Returns:
            Combined and ranked results
        """
        fused = {}
        rank_constant = 20

        def get_record(document_id, document, metadata):
            key = document_id or ("text", document)
            if key not in fused:
                fused[key] = {
                    "id": document_id,
                    "document": document,
                    "metadata": metadata.copy() if metadata else {},
                    "bm25_score": 0.0,
                    "vector_score": 0.0,
                    "fusion_score": 0.0,
                }
            elif metadata and not fused[key]["metadata"]:
                fused[key]["metadata"] = metadata.copy()
            return fused[key]

        max_bm25 = max((result["score"] for result in bm25_results), default=0.0)
        for rank, result in enumerate(bm25_results, start=1):
            record = get_record(result.get("id"), result["document"], result.get("metadata"))
            record["bm25_score"] = result["score"] / max_bm25 if max_bm25 > 0 else 0.0
            record["fusion_score"] += (1.0 - alpha) / (rank_constant + rank)

        for rank, (document, distance, metadata, document_id) in enumerate(
            zip(vector_docs, vector_scores, vector_metadata, vector_ids), start=1
        ):
            record = get_record(document_id, document, metadata)
            record["vector_score"] = max(0.0, 1.0 - float(distance))
            record["fusion_score"] += alpha / (rank_constant + rank)

        combined_results = []
        for record in fused.values():
            record["combined_score"] = (
                (1.0 - alpha) * record["bm25_score"]
                + alpha * record["vector_score"]
            )
            if record["combined_score"] >= self.MIN_RELEVANCE_SCORE:
                combined_results.append(record)

        combined_results.sort(
            key=lambda result: (result["fusion_score"], result["combined_score"]),
            reverse=True,
        )
        return combined_results
    
    def is_ready(self) -> bool:
        """Check if retriever is ready"""
        return self.is_indexed
