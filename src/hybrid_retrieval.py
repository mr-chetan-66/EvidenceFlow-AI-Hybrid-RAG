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
        
    def index_documents(self, documents: List[str]):
        """
        Index documents for both BM25 and vector search
        
        Args:
            documents: List of document strings
        """
        # Index for BM25
        self.bm25.index_documents(documents)
        self.is_indexed = True
        
    def retrieve(
        self, 
        query: str, 
        k: int = 10, 
        alpha: float = 0.5
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
            
        # BM25 retrieval
        bm25_results = self.bm25.search(query, k=k)
        
        # Vector retrieval
        query_embedding = self.embedding_manager.genetate_embedding([query])[0]
        vector_results = self.vectorstore.similar_search(query_embedding, n_results=k)
        
        # Convert vector results to standard format
        vector_docs = vector_results['documents'][0]
        vector_scores = vector_results['distances'][0] if 'distances' in vector_results else [1.0] * len(vector_docs)
        vector_metadata = vector_results['metadatas'][0] if 'metadatas' in vector_results else [{}] * len(vector_docs)
        
        # Normalize and combine scores
        combined_results = self._combine_results(
            bm25_results, 
            vector_docs, 
            vector_scores, 
            vector_metadata,
            alpha
        )
        
        # Prepare metadata
        retrieval_metadata = {
            'bm25_count': len(bm25_results),
            'vector_count': len(vector_docs),
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
        # Create score dictionary with metadata
        score_dict = {}
        
        # Add BM25 scores (without metadata)
        max_bm25 = max([r['score'] for r in bm25_results]) if bm25_results else 1.0
        for result in bm25_results:
            doc = result['document']
            normalized_score = result['score'] / max_bm25 if max_bm25 > 0 else 0
            if doc not in score_dict:
                score_dict[doc] = {
                    'bm25_score': normalized_score,
                    'vector_score': 0.0,
                    'metadata': {}  # BM25 doesn't have metadata
                }
            else:
                score_dict[doc]['bm25_score'] = normalized_score
        
        # Add vector scores with metadata (this is where we get source and page info)
        max_vector = max(vector_scores) if vector_scores else 1.0
        for doc, score, meta in zip(vector_docs, vector_scores, vector_metadata):
            # Convert distance to similarity (lower distance = higher similarity)
            normalized_score = 1.0 - (score / max_vector) if max_vector > 0 else 0
            if doc not in score_dict:
                score_dict[doc] = {
                    'bm25_score': 0.0,
                    'vector_score': normalized_score,
                    'metadata': meta.copy() if meta else {}  # Copy metadata
                }
            else:
                score_dict[doc]['vector_score'] = normalized_score
                # Always prefer vector metadata as it contains source and page info
                if meta:
                    score_dict[doc]['metadata'] = meta.copy()
        
        # Combine scores
        combined_results = []
        for doc, scores in score_dict.items():
            combined_score = alpha * scores['vector_score'] + (1 - alpha) * scores['bm25_score']
            combined_results.append({
                'document': doc,
                'combined_score': combined_score,
                'bm25_score': scores['bm25_score'],
                'vector_score': scores['vector_score'],
                'metadata': scores['metadata']
            })
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return combined_results
    
    def is_ready(self) -> bool:
        """Check if retriever is ready"""
        return self.is_indexed
