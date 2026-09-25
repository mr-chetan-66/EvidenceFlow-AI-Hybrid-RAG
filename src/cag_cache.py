"""
Cache-Augmented Generation (CAG) Module
Implements semantic caching for frequently asked questions and verified responses
"""
from typing import List, Dict, Any, Optional
import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from src.embedding import EmbeddingManager
import os


class CAGCache:
    def __init__(self, cache_dir: str = None, embedding_manager: EmbeddingManager = None):
        """
        Initialize CAG cache
        
        Args:
            cache_dir: Directory to store cache files
            embedding_manager: EmbeddingManager for semantic similarity
        """
        if cache_dir is None:
            project_root = Path(__file__).resolve().parents[1]
            # Check if running on Render (has mounted disk)
            render_disk_path = os.getenv("RENDER_DISK_PATH", "/opt/render/project/data")
            if os.path.exists(render_disk_path):
                cache_dir = str(Path(render_disk_path) / "cag_cache")
            else:
                cache_dir = str(project_root / "data" / "cag_cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_manager = embedding_manager or EmbeddingManager()
        self.cache_file = self.cache_dir / "cache.json"
        self.cache_data = self._load_cache()
        
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")
                return {'queries': {}, 'metadata': {'version': '1.0'}}
        else:
            return {'queries': {}, 'metadata': {'version': '1.0'}}
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _generate_query_hash(self, query: str) -> str:
        """Generate hash for query"""
        return hashlib.sha256(query.encode('utf-8')).hexdigest()
    
    def get(
        self, 
        query: str, 
        similarity_threshold: float = 0.85
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for query (exact match or semantic similarity)
        
        Args:
            query: Query string
            similarity_threshold: Threshold for semantic similarity
            
        Returns:
            Cached response dict or None
        """
        # Try exact hash match first
        query_hash = self._generate_query_hash(query)
        if query_hash in self.cache_data['queries']:
            cached = self.cache_data['queries'][query_hash]
            cached['cache_hit'] = 'exact'
            cached['cache_time'] = datetime.now().isoformat()
            return cached
        
        # Try semantic similarity
        if self.embedding_manager:
            cached_entry = self._find_semantic_match(query, similarity_threshold)
            if cached_entry:
                cached_entry['cache_hit'] = 'semantic'
                cached_entry['cache_time'] = datetime.now().isoformat()
                return cached_entry
        
        return None
    
    def _find_semantic_match(
        self, 
        query: str, 
        threshold: float
    ) -> Optional[Dict[str, Any]]:
        """
        Find semantically similar cached query
        
        Args:
            query: Query string
            threshold: Similarity threshold
            
        Returns:
            Cached entry or None
        """
        if not self.cache_data['queries']:
            return None
        
        # Get query embedding
        query_embedding = self.embedding_manager.genetate_embedding([query])[0]
        
        # Compare with cached queries
        best_match = None
        best_similarity = 0.0
        
        for query_hash, cached in self.cache_data['queries'].items():
            if 'query_embedding' not in cached:
                continue
                
            cached_embedding = np.array(cached['query_embedding'])
            similarity = np.dot(query_embedding, cached_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(cached_embedding)
            )
            
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = cached
                best_match['similarity'] = similarity
        
        return best_match
    
    def set(
        self, 
        query: str, 
        response: str, 
        evidence: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Cache a query-response pair
        
        Args:
            query: Query string
            response: Generated response
            evidence: Retrieved evidence
            metadata: Additional metadata
        """
        query_hash = self._generate_query_hash(query)
        
        # Generate query embedding for semantic matching
        query_embedding = self.embedding_manager.genetate_embedding([query])[0]
        
        # Prepare cache entry with full evidence metadata
        cache_entry = {
            'query': query,
            'query_embedding': query_embedding.tolist(),
            'response': response,
            'evidence': evidence or [],
            'metadata': {
                **(metadata or {}),
                'evidence_grade': metadata.get('evidence_grade', {
                    'overall_quality': 0.8,
                    'relevance_score': 0.8,
                    'coverage_score': 0.8,
                    'diversity_score': 0.8,
                    'is_sufficient': True
                }),
                'citation_verification': metadata.get('citation_verification', {
                    'is_supported': True,
                    'confidence': 0.8,
                    'unsupported_claims': [],
                    'verification_details': 'Cached result',
                    'evidence_count': len(evidence or []),
                    'citations': []  # Will be extracted on retrieval
                })
            },
            'created_at': datetime.now().isoformat(),
            'access_count': 0
        }
        
        # Store in cache
        self.cache_data['queries'][query_hash] = cache_entry
        self._save_cache()
    
    def increment_access(self, query: str):
        """Increment access count for cached query"""
        query_hash = self._generate_query_hash(query)
        if query_hash in self.cache_data['queries']:
            self.cache_data['queries'][query_hash]['access_count'] += 1
            self.cache_data['queries'][query_hash]['last_accessed'] = datetime.now().isoformat()
            self._save_cache()
    
    def invalidate(self, query: str = None):
        """
        Invalidate cache entry
        
        Args:
            query: Specific query to invalidate (None = clear all)
        """
        if query is None:
            # Clear all cache
            self.cache_data = {'queries': {}, 'metadata': {'version': '1.0'}}
        else:
            # Remove specific query
            query_hash = self._generate_query_hash(query)
            if query_hash in self.cache_data['queries']:
                del self.cache_data['queries'][query_hash]
        
        self._save_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_queries = len(self.cache_data['queries'])
        total_access = sum(
            entry.get('access_count', 0) 
            for entry in self.cache_data['queries'].values()
        )
        
        return {
            'total_cached_queries': total_queries,
            'total_access_count': total_access,
            'avg_access_per_query': total_access / total_queries if total_queries > 0 else 0,
            'cache_file_size': self.cache_file.stat().st_size if self.cache_file.exists() else 0
        }
    
    def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent cache entries"""
        entries = list(self.cache_data['queries'].values())
        entries.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return entries[:limit]
    
    def extract_citations_from_evidence(self, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract citation information from evidence for display"""
        citations = []
        for i, doc in enumerate(evidence):
            if isinstance(doc, dict):
                metadata = doc.get('metadata', {})
                source = metadata.get('source', 'unknown')
                page = metadata.get('page', 'N/A')
                score = doc.get('combined_score', doc.get('score', 0.0))
                text = doc.get('document', '')
            else:
                source = 'unknown'
                page = 'N/A'
                score = 0.0
                text = str(doc)[:200] if len(str(doc)) > 200 else str(doc)
            
            # Clean up source path
            if source != 'unknown':
                source = source.split('\\')[-1].split('/')[-1]
            
            # Convert page to integer if possible
            try:
                page_num = int(page) if page != 'N/A' else 'N/A'
            except (ValueError, TypeError):
                page_num = page
            
            citations.append({
                'index': i,
                'source': source,
                'page': page_num,
                'score': score,
                'text': text[:200] + '...' if len(text) > 200 else text
            })
        return citations
