"""
BM25 Keyword Search Module
Implements BM25 algorithm for keyword-based retrieval
"""
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np


class BM25Search:
    def __init__(self):
        self.bm25 = None
        self.documents = []
        self.tokenized_docs = []
        
    def index_documents(self, documents: List[str]):
        """
        Index documents for BM25 search
        
        Args:
            documents: List of document text strings
        """
        self.documents = documents
        # Tokenize documents (simple whitespace tokenization)
        self.tokenized_docs = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)
        
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search using BM25
        
        Args:
            query: Search query string
            k: Number of results to return
            
        Returns:
            List of dictionaries with scores and indices
        """
        if self.bm25 is None:
            raise ValueError("BM25 index not built. Call index_documents first.")
            
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:k]
        
        # Format results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only return results with positive scores
                results.append({
                    'index': int(idx),
                    'score': float(scores[idx]),
                    'document': self.documents[idx]
                })
                
        return results
    
    def is_indexed(self) -> bool:
        """Check if BM25 index is built"""
        return self.bm25 is not None
