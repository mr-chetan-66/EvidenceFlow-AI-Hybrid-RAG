"""
BM25 Keyword Search Module
Implements BM25 algorithm for keyword-based retrieval
"""
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np
import re


class BM25Search:
    STOP_WORDS = {
        "a", "about", "an", "and", "are", "as", "at", "be", "by", "can",
        "could", "did", "do", "does", "for", "from", "give", "how", "i",
        "in", "is", "it", "me", "of", "on", "or", "please", "the", "this",
        "to", "was", "what", "when", "where", "which", "who", "why", "with",
        "would",
    }

    def __init__(self):
        self.bm25 = None
        self.documents = []
        self.tokenized_docs = []
        self.metadatas = []
        self.document_ids = []

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        return [
            token for token in re.findall(r"[a-z0-9]+", text.lower())
            if token not in cls.STOP_WORDS
        ]
        
    def index_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]] = None,
        document_ids: List[str] = None,
    ):
        """
        Index documents for BM25 search
        
        Args:
            documents: List of document text strings
        """
        metadatas = metadatas or [{} for _ in documents]
        document_ids = document_ids or [None for _ in documents]
        if len(metadatas) != len(documents) or len(document_ids) != len(documents):
            raise ValueError("Documents, metadata, and IDs must have matching lengths")

        indexed_records = [
            (document, metadata, document_id, self.tokenize(document))
            for document, metadata, document_id in zip(documents, metadatas, document_ids)
        ]
        indexed_records = [record for record in indexed_records if record[3]]
        self.documents = [record[0] for record in indexed_records]
        self.metadatas = [record[1] for record in indexed_records]
        self.document_ids = [record[2] for record in indexed_records]
        self.tokenized_docs = [record[3] for record in indexed_records]
        self.bm25 = BM25Okapi(self.tokenized_docs) if self.tokenized_docs else None
        
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
            return []
            
        tokenized_query = self.tokenize(query)
        if not tokenized_query:
            return []
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices
        top_indices = np.argsort(-scores, kind="stable")[:k]
        
        # Format results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only return results with positive scores
                results.append({
                    'index': int(idx),
                    'score': float(scores[idx]),
                    'document': self.documents[idx],
                    'metadata': self.metadatas[idx],
                    'id': self.document_ids[idx],
                })
                
        return results
    
    def is_indexed(self) -> bool:
        """Check if BM25 index is built"""
        return self.bm25 is not None
