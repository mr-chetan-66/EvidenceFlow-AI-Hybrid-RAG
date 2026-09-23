"""
Reranker Module
Implements document reranking to improve retrieval relevance
"""
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
import cohere

load_dotenv()


class Reranker:
    def __init__(self, api_key: str = None):
        """
        Initialize Cohere reranker
        
        Args:
            api_key: Cohere API key (defaults to COHERE_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        if self.api_key:
            self.client = cohere.Client(self.api_key)
        else:
            self.client = None
            print("Warning: No Cohere API key provided. Reranking will be disabled.")
            
    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank documents based on query relevance
        
        Args:
            query: Search query
            documents: List of document strings
            top_k: Number of top results to return
            
        Returns:
            List of reranked documents with scores
        """
        if self.client is None:
            # Fallback: return documents in original order with dummy scores
            return [
                {
                    'index': i,
                    'document': doc,
                    'score': 1.0 - (i * 0.1)  # Decreasing dummy scores
                }
                for i, doc in enumerate(documents[:top_k])
            ]
            
        try:
            # Call Cohere rerank API with updated model
            response = self.client.rerank(
                model="rerank-english-v3.0",  # Updated to current model
                query=query,
                documents=documents,
                top_n=top_k
            )
            
            # Format results
            results = []
            for result in response.results:
                results.append({
                    'index': result.index,
                    'document': documents[result.index],
                    'score': result.relevance_score
                })
                
            return results
            
        except Exception as e:
            print(f"Reranking error: {e}")
            # Fallback to original order
            return [
                {
                    'index': i,
                    'document': doc,
                    'score': 1.0 - (i * 0.1)
                }
                for i, doc in enumerate(documents[:top_k])
            ]
    
    def is_available(self) -> bool:
        """Check if reranker is available"""
        return self.client is not None
