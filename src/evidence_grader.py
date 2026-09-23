"""
Evidence Grading Module
Evaluates the quality and relevance of retrieved evidence
"""
from typing import List, Dict, Any
import numpy as np


class EvidenceGrader:
    def __init__(self):
        """Initialize evidence grader"""
        pass
        
    def grade_evidence(
        self, 
        query: str, 
        retrieved_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Grade the quality of retrieved evidence
        
        Args:
            query: Original query
            retrieved_docs: List of retrieved documents with scores
            
        Returns:
            Dictionary with evidence quality metrics
        """
        if not retrieved_docs:
            return {
                'overall_quality': 0.0,
                'relevance_score': 0.0,
                'coverage_score': 0.0,
                'diversity_score': 0.0,
                'confidence': 0.0,
                'is_sufficient': False
            }
        
        # Calculate various quality metrics
        relevance_score = self._calculate_relevance(query, retrieved_docs)
        coverage_score = self._calculate_coverage(retrieved_docs)
        diversity_score = self._calculate_diversity(retrieved_docs)
        
        # Calculate overall quality (weighted average)
        overall_quality = (
            0.5 * relevance_score +
            0.3 * coverage_score +
            0.2 * diversity_score
        )
        
        # Determine if evidence is sufficient
        is_sufficient = overall_quality > 0.5 and len(retrieved_docs) >= 3
        
        return {
            'overall_quality': overall_quality,
            'relevance_score': relevance_score,
            'coverage_score': coverage_score,
            'diversity_score': diversity_score,
            'confidence': overall_quality,
            'is_sufficient': is_sufficient,
            'doc_count': len(retrieved_docs)
        }
    
    def _calculate_relevance(
        self, 
        query: str, 
        retrieved_docs: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate relevance score based on retrieval scores
        
        Args:
            query: Original query
            retrieved_docs: Retrieved documents
            
        Returns:
            Relevance score (0-1)
        """
        if not retrieved_docs:
            return 0.0
        
        # Use combined scores if available, otherwise use fallback
        scores = []
        for doc in retrieved_docs:
            if 'combined_score' in doc:
                scores.append(doc['combined_score'])
            elif 'score' in doc:
                scores.append(doc['score'])
            else:
                scores.append(0.5)  # Default fallback
        
        # Average of top 3 scores
        top_scores = sorted(scores, reverse=True)[:3]
        avg_score = np.mean(top_scores) if top_scores else 0.0
        
        return min(avg_score, 1.0)
    
    def _calculate_coverage(
        self, 
        retrieved_docs: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate coverage score based on document diversity
        
        Args:
            retrieved_docs: Retrieved documents
            
        Returns:
            Coverage score (0-1)
        """
        if not retrieved_docs:
            return 0.0
        
        # Check if documents come from different sources/pages
        sources = set()
        for doc in retrieved_docs:
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'unknown')
            page = metadata.get('page', 0)
            sources.add(f"{source}_page_{page}")
        
        # Coverage based on source diversity
        unique_sources = len(sources)
        max_possible = min(len(retrieved_docs), 5)  # Cap at 5 unique sources
        
        coverage = unique_sources / max_possible if max_possible > 0 else 0.0
        
        return coverage
    
    def _calculate_diversity(
        self, 
        retrieved_docs: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate diversity score based on content variety
        
        Args:
            retrieved_docs: Retrieved documents
            
        Returns:
            Diversity score (0-1)
        """
        if len(retrieved_docs) <= 1:
            return 0.0
        
        # Calculate average document length
        doc_lengths = [len(doc.get('document', '')) for doc in retrieved_docs]
        avg_length = np.mean(doc_lengths) if doc_lengths else 0
        
        # Check for length variety (avoid too short or too similar documents)
        length_std = np.std(doc_lengths) if len(doc_lengths) > 1 else 0
        diversity = min(length_std / (avg_length + 1), 1.0) if avg_length > 0 else 0.0
        
        return diversity
    
    def get_evidence_summary(
        self, 
        retrieved_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Get a human-readable summary of evidence
        
        Args:
            retrieved_docs: Retrieved documents
            
        Returns:
            Summary string
        """
        if not retrieved_docs:
            return "No evidence retrieved."
        
        summary_parts = []
        
        # Count unique sources
        sources = set()
        for doc in retrieved_docs:
            metadata = doc.get('metadata', {})
            source = metadata.get('source', 'unknown')
            sources.add(source.split('/')[-1])  # Just filename
        
        summary_parts.append(f"Retrieved {len(retrieved_docs)} evidence chunks")
        summary_parts.append(f"From {len(sources)} unique document(s)")
        
        # Average score
        scores = [doc.get('combined_score', doc.get('score', 0.5)) for doc in retrieved_docs]
        avg_score = np.mean(scores) if scores else 0.0
        summary_parts.append(f"Average relevance: {avg_score:.2f}")
        
        return " | ".join(summary_parts)
