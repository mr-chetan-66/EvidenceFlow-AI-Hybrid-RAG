"""
Agentic Retrieval Module
Implements intelligent retrieval loop with query rewriting and iterative refinement
"""
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from src.hybrid_retrieval import HybridRetriever
from src.reranker import Reranker
from src.evidence_grader import EvidenceGrader
from src.citation_verifier import CitationVerifier
from src.cag_cache import CAGCache

load_dotenv()


class AgenticRetrieval:
    def __init__(
        self,
        hybrid_retriever: HybridRetriever,
        max_iterations: int = 2,  # Reduced from 3 for speed
        enable_cache: bool = True,  # Re-enable cache
        enable_reranking: bool = True,  # Optional reranking
        enable_citation_check: bool = False  # Disabled by default for speed
    ):
        """
        Initialize agentic retrieval system - optimized for speed
        
        Args:
            hybrid_retriever: HybridRetriever instance
            max_iterations: Maximum retrieval iterations (reduced to 2)
            enable_cache: Enable CAG cache
            enable_reranking: Enable reranking (can be disabled for speed)
            enable_citation_check: Enable citation verification (disabled for speed)
        """
        self.hybrid_retriever = hybrid_retriever
        self.max_iterations = max_iterations
        self.enable_cache = enable_cache
        self.enable_reranking = enable_reranking
        self.enable_citation_check = enable_citation_check
        
        # Initialize components
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="openai/gpt-oss-20b",
            temperature=0.3,
            max_tokens=1024
        )
        
        # Optional components
        self.reranker = Reranker() if enable_reranking else None
        self.evidence_grader = EvidenceGrader()
        self.citation_verifier = CitationVerifier() if enable_citation_check else None
        
        # Initialize cache if enabled
        if enable_cache:
            self.cache = CAGCache(
                embedding_manager=self.hybrid_retriever.embedding_manager
            )
        else:
            self.cache = None
    
    def retrieve_and_answer(
        self,
        query: str,
        k: int = 10,
        alpha: float = 0.5
    ) -> Dict[str, Any]:
        """
        Main agentic retrieval loop
        
        Args:
            query: User query
            k: Number of documents to retrieve
            alpha: Hybrid retrieval weight
            
        Returns:
            Dictionary with answer, evidence, and metadata
        """
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(query)
            if cached_result:
                self.cache.increment_access(query)
                # Extract citations from evidence for display
                citations = self.cache.extract_citations_from_evidence(cached_result.get('evidence', []))
                
                return {
                    'answer': cached_result['response'],
                    'evidence': cached_result['evidence'],
                    'cache_hit': 'exact',  # Force exact hit for cache results
                    'iterations': 0,
                    'confidence': cached_result.get('metadata', {}).get('confidence', 0.8),
                    'evidence_grade': cached_result.get('metadata', {}).get('evidence_grade', {
                        'overall_quality': 0.8,
                        'relevance_score': 0.8,
                        'coverage_score': 0.8,
                        'diversity_score': 0.8,
                        'is_sufficient': True
                    }),
                    'citation_verification': cached_result.get('metadata', {}).get('citation_verification', {
                        'is_supported': True,
                        'confidence': 0.8,
                        'unsupported_claims': [],
                        'verification_details': 'Cached result',
                        'evidence_count': len(cached_result.get('evidence', [])),
                        'citations': citations
                    }),
                    'metadata': cached_result.get('metadata', {})
                }
        
        # Agentic retrieval loop
        retrieval_history = []
        current_query = query
        
        for iteration in range(self.max_iterations):
            # Retrieve evidence
            retrieved_docs, retrieval_metadata = self.hybrid_retriever.retrieve(
                current_query,
                k=k,
                alpha=alpha
            )
            
            # Grade evidence quality
            evidence_grade = self.evidence_grader.grade_evidence(
                current_query,
                retrieved_docs
            )
            
            # Store iteration history
            retrieval_history.append({
                'iteration': iteration + 1,
                'query': current_query,
                'doc_count': len(retrieved_docs),
                'evidence_grade': evidence_grade,
                'retrieval_metadata': retrieval_metadata
            })
            
            # Check if evidence is sufficient
            if evidence_grade['is_sufficient']:
                break
            
            # If not sufficient and not last iteration, rewrite query
            if iteration < self.max_iterations - 1:
                current_query = self._rewrite_query(
                    original_query=query,
                    current_query=current_query,
                    evidence_grade=evidence_grade,
                    retrieved_docs=retrieved_docs
                )
        
        # Rerank top results (optional)
        if self.enable_reranking and self.reranker:
            top_docs = retrieved_docs[:5]
            reranked_results = self.reranker.rerank(
                query,
                [doc['document'] for doc in top_docs],
                top_k=5
            )
            # Preserve metadata from original documents
            reranked_docs = []
            for reranked in reranked_results:
                original_doc = top_docs[reranked['index']]
                reranked_docs.append({
                    'document': reranked['document'],
                    'combined_score': reranked['score'],
                    'metadata': original_doc.get('metadata', {}),
                    'bm25_score': original_doc.get('bm25_score', 0.0),
                    'vector_score': original_doc.get('vector_score', 0.0)
                })
        else:
            reranked_docs = retrieved_docs[:5]
        
        # Generate answer
        answer = self._generate_answer(query, reranked_docs)
        
        # Verify citations (optional)
        if self.enable_citation_check and self.citation_verifier:
            citation_verification = self.citation_verifier.verify_citations(
                answer,
                reranked_docs
            )
        else:
            citation_verification = {
                'is_supported': True,
                'confidence': 0.8,
                'unsupported_claims': [],
                'verification_details': 'Citation verification disabled for speed',
                'evidence_count': len(reranked_docs),
                'citations': self._extract_simple_citations(reranked_docs)
            }
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            evidence_grade,
            citation_verification,
            len(retrieval_history)
        )
        
        # Prepare result
        result = {
            'answer': answer,
            'evidence': reranked_docs,
            'cache_hit': 'miss',
            'iterations': len(retrieval_history),
            'retrieval_history': retrieval_history,
            'evidence_grade': evidence_grade,
            'citation_verification': citation_verification,
            'confidence': confidence,
            'metadata': {
                'original_query': query,
                'final_query': current_query,
                'retrieval_metadata': retrieval_metadata
            }
        }
        
        # Cache the result if enabled
        if self.cache and confidence > 0.5:
            self.cache.set(
                query=query,
                response=answer,
                evidence=reranked_docs,
                metadata={
                    'confidence': confidence,
                    'iterations': len(retrieval_history),
                    'evidence_grade': evidence_grade,
                    'citation_verification': citation_verification
                }
            )
        
        return result
    
    def _rewrite_query(
        self,
        original_query: str,
        current_query: str,
        evidence_grade: Dict[str, Any],
        retrieved_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Rewrite query to improve retrieval
        
        Args:
            original_query: Original user query
            current_query: Current query being used
            evidence_grade: Evidence quality assessment
            retrieved_docs: Currently retrieved documents
            
        Returns:
            Rewritten query string
        """
        # Get evidence summary
        evidence_summary = self.evidence_grader.get_evidence_summary(retrieved_docs)
        
        rewrite_prompt = f"""
You are a query rewriting expert. Your task is to improve a search query based on retrieval feedback.

Original Query: {original_query}
Current Query: {current_query}

Evidence Quality Assessment:
- Overall Quality: {evidence_grade['overall_quality']:.2f}
- Relevance: {evidence_grade['relevance_score']:.2f}
- Coverage: {evidence_grade['coverage_score']:.2f}
- Diversity: {evidence_grade['diversity_score']:.2f}

Evidence Summary: {evidence_summary}

Instructions:
1. Analyze why the current retrieval is insufficient
2. Rewrite the query to be more specific, use different keywords, or change the focus
3. Keep the semantic meaning but improve retrieval potential
4. Return ONLY the rewritten query (no explanation)

Rewritten Query:
"""
        
        try:
            response = self.llm.invoke(rewrite_prompt)
            rewritten_query = response.content.strip()
            
            # If rewriting failed or returned same query, add query expansion
            if not rewritten_query or rewritten_query == current_query:
                # Add relevant terms from retrieved docs
                expanded_query = self._expand_query(current_query, retrieved_docs)
                return expanded_query
            
            return rewritten_query
            
        except Exception as e:
            print(f"Query rewriting error: {e}")
            # Fallback to query expansion
            return self._expand_query(current_query, retrieved_docs)
    
    def _expand_query(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> str:
        """
        Expand query with terms from retrieved documents
        
        Args:
            query: Original query
            retrieved_docs: Retrieved documents
            
        Returns:
            Expanded query
        """
        # Extract key terms from top documents
        top_docs = retrieved_docs[:3]
        all_text = " ".join([doc['document'] for doc in top_docs])
        
        # Simple expansion: add words from documents that aren't in query
        query_words = set(query.lower().split())
        doc_words = set(all_text.lower().split())
        
        # Add up to 3 new relevant words
        new_words = list(doc_words - query_words)[:3]
        
        if new_words:
            expanded_query = query + " " + " ".join(new_words)
            return expanded_query
        
        return query
    
    def _generate_answer(
        self,
        query: str,
        evidence: List[Dict[str, Any]]
    ) -> str:
        """
        Generate answer using retrieved evidence
        
        Args:
            query: User query
            evidence: Reranked evidence documents
            
        Returns:
            Generated answer
        """
        # Prepare evidence context
        evidence_text = "\n\n".join([
            f"[{i}] {doc['document']}"
            for i, doc in enumerate(evidence)
        ])
        
        answer_prompt = f"""
You are a helpful question-answering assistant that provides accurate, well-cited answers.

Question: {query}

Evidence:
{evidence_text}

Instructions:
1. Answer the question using ONLY the provided evidence
2. Cite the evidence using [0], [1], etc. references
3. If the evidence is insufficient, state that clearly
4. Do not hallucinate or use outside knowledge
5. Be concise but comprehensive

Answer:
"""
        
        try:
            response = self.llm.invoke(answer_prompt)
            return response.content.strip()
        except Exception as e:
            print(f"Answer generation error: {e}")
            return "I apologize, but I encountered an error generating the answer. Please try again."
    
    def _calculate_confidence(
        self,
        evidence_grade: Dict[str, Any],
        citation_verification: Dict[str, Any],
        iterations: int
    ) -> float:
        """
        Calculate overall confidence score
        
        Args:
            evidence_grade: Evidence quality assessment
            citation_verification: Citation verification results
            iterations: Number of retrieval iterations
            
        Returns:
            Confidence score (0-1)
        """
        # Evidence quality weight: 0.4
        evidence_confidence = evidence_grade['overall_quality']
        
        # Citation verification weight: 0.4
        citation_confidence = citation_verification.get('confidence', 0.5)
        if citation_verification.get('is_supported', False):
            citation_confidence = min(citation_confidence + 0.2, 1.0)
        
        # Iteration penalty: fewer iterations is better
        iteration_penalty = 1.0 - (iterations * 0.1)
        iteration_penalty = max(iteration_penalty, 0.5)
        
        # Calculate weighted average
        confidence = (
            0.4 * evidence_confidence +
            0.4 * citation_confidence +
            0.2 * iteration_penalty
        )
        
        return round(confidence, 2)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {'enabled': False}
    
    def _extract_simple_citations(self, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract simple citation information from evidence"""
        citations = []
        for i, doc in enumerate(evidence):
            # Handle both dict and possible string/document objects
            if isinstance(doc, dict):
                metadata = doc.get('metadata', {})
                source = metadata.get('source', 'unknown')
                page = metadata.get('page', 'N/A')
                score = doc.get('combined_score', doc.get('score', 0.0))
                text = doc.get('document', '')
            else:
                # Fallback for unexpected formats
                source = 'unknown'
                page = 'N/A'
                score = 0.0
                text = str(doc)[:200] if len(str(doc)) > 200 else str(doc)
            
            # Clean up source path for display
            if source != 'unknown':
                source = source.split('\\')[-1].split('/')[-1]  # Get just filename
            
            # Convert page to integer if possible, otherwise keep as string
            try:
                page_num = int(page) if page != 'N/A' else 'N/A'
            except (ValueError, TypeError):
                page_num = page
            
            citation = {
                'index': i,
                'source': source,
                'page': page_num,
                'score': score,
                'text': text[:200] + '...' if len(text) > 200 else text
            }
            citations.append(citation)
        return citations
