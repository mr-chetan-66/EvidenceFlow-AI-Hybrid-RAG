"""
Cache-Augmented Generation (CAG) Module
Implements semantic caching for frequently asked questions and verified responses
"""
from typing import List, Dict, Any, Optional
import json
import hashlib
from pathlib import Path
from datetime import datetime
from src.embedding import EmbeddingManager
from src.storage_paths import get_data_root
import os


class CAGCache:
    CACHE_VERSION = "3.0"

    def __init__(self, cache_dir: str = None, embedding_manager: EmbeddingManager = None):
        """
        Initialize CAG cache
        
        Args:
            cache_dir: Directory to store cache files
            embedding_manager: EmbeddingManager for semantic similarity
        """
        if cache_dir is None:
            cache_dir = str(get_data_root() / "cag_cache")
        
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
                    cache_data = json.load(f)
                if cache_data.get('metadata', {}).get('version') != self.CACHE_VERSION:
                    return {'queries': {}, 'metadata': {'version': self.CACHE_VERSION}}
                return cache_data
            except Exception as e:
                print(f"Error loading cache: {e}")
                return {'queries': {}, 'metadata': {'version': self.CACHE_VERSION}}
        else:
            return {'queries': {}, 'metadata': {'version': self.CACHE_VERSION}}
    
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
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached response only for an exact query match.
        
        Args:
            query: Query string
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
        
        return None
    
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
        metadata = metadata or {}
        
        # Prepare cache entry with full evidence metadata
        cache_entry = {
            'query': query,
            'response': response,
            'evidence': evidence or [],
            'metadata': {
                **(metadata or {}),
                'evidence_grade': metadata.get('evidence_grade', {
                    'overall_quality': 0.0,
                    'relevance_score': 0.0,
                    'coverage_score': 0.0,
                    'diversity_score': 0.0,
                    'is_sufficient': False
                }),
                'citation_verification': metadata.get('citation_verification', {
                    'is_supported': None,
                    'confidence': 0.0,
                    'unsupported_claims': [],
                    'verification_details': 'Citation verification was not run before caching.',
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
            self.cache_data = {'queries': {}, 'metadata': {'version': self.CACHE_VERSION}}
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
