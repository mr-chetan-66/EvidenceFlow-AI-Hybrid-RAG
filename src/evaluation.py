"""
Evaluation Module
Comprehensive evaluation system for testing RAG performance
"""
from typing import List, Dict, Any, Tuple
import time
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np


class EvaluationSystem:
    def __init__(self, agentic_retrieval):
        """
        Initialize evaluation system
        
        Args:
            agentic_retrieval: AgenticRetrieval instance
        """
        self.agentic_retrieval = agentic_retrieval
        self.results = []
        
    def run_evaluation(
        self,
        questions: List[str],
        expected_answers: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run evaluation on a set of questions
        
        Args:
            questions: List of test questions
            expected_answers: Optional list of expected answers for accuracy comparison
            
        Returns:
            Dictionary with evaluation results and metrics
        """
        self.results = []
        
        for i, question in enumerate(questions):
            print(f"Processing question {i+1}/{len(questions)}")
            
            start_time = time.time()
            
            try:
                result = self.agentic_retrieval.retrieve_and_answer(
                    question,
                    k=10,
                    alpha=0.5
                )
                
                end_time = time.time()
                
                # Calculate metrics
                metrics = {
                    'question': question,
                    'answer': result['answer'],
                    'confidence': result['confidence'],
                    'cache_hit': result['cache_hit'],
                    'iterations': result['iterations'],
                    'latency': end_time - start_time,
                    'evidence_quality': result['evidence_grade']['overall_quality'],
                    'evidence_relevance': result['evidence_grade']['relevance_score'],
                    'evidence_coverage': result['evidence_grade']['coverage_score'],
                    'evidence_diversity': result['evidence_grade']['diversity_score'],
                    'citation_supported': result['citation_verification']['is_supported'],
                    'citation_confidence': result['citation_verification'].get('confidence', 0.0),
                    'evidence_count': len(result['evidence']),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add expected answer comparison if provided
                if expected_answers and i < len(expected_answers):
                    metrics['expected_answer'] = expected_answers[i]
                    metrics['answer_similarity'] = self._calculate_similarity(
                        result['answer'],
                        expected_answers[i]
                    )
                
                self.results.append(metrics)
                
            except Exception as e:
                print(f"Error processing question: {e}")
                self.results.append({
                    'question': question,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Calculate aggregate metrics
        return self._calculate_aggregate_metrics()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_aggregate_metrics(self) -> Dict[str, Any]:
        """
        Calculate aggregate metrics from results
        
        Returns:
            Dictionary with aggregate metrics
        """
        successful_results = [r for r in self.results if 'error' not in r]
        
        if not successful_results:
            return {
                'total_questions': len(self.results),
                'successful': 0,
                'failed': len(self.results),
                'error': 'No successful results'
            }
        
        # Calculate averages
        metrics = {
            'total_questions': len(self.results),
            'successful': len(successful_results),
            'failed': len(self.results) - len(successful_results),
            'avg_confidence': np.mean([r['confidence'] for r in successful_results]),
            'avg_latency': np.mean([r['latency'] for r in successful_results]),
            'avg_iterations': np.mean([r['iterations'] for r in successful_results]),
            'avg_evidence_quality': np.mean([r['evidence_quality'] for r in successful_results]),
            'avg_evidence_relevance': np.mean([r['evidence_relevance'] for r in successful_results]),
            'avg_evidence_coverage': np.mean([r['evidence_coverage'] for r in successful_results]),
            'avg_evidence_diversity': np.mean([r['evidence_diversity'] for r in successful_results]),
            'citation_support_rate': sum(1 for r in successful_results if r['citation_supported']) / len(successful_results),
            'cache_hit_rate': sum(1 for r in successful_results if r['cache_hit'] != 'miss') / len(successful_results)
        }
        
        # Add answer similarity if available
        if 'answer_similarity' in successful_results[0]:
            metrics['avg_answer_similarity'] = np.mean([r['answer_similarity'] for r in successful_results])
        
        return metrics
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """Get results as pandas DataFrame"""
        return pd.DataFrame(self.results)
    
    def save_results(self, filepath: str):
        """
        Save evaluation results to file
        
        Args:
            filepath: Path to save results
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to {filepath}")
    
    def load_results(self, filepath: str):
        """
        Load evaluation results from file
        
        Args:
            filepath: Path to load results from
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            self.results = json.load(f)
        
        print(f"Results loaded from {filepath}")
    
    def generate_report(self) -> str:
        """
        Generate human-readable evaluation report
        
        Returns:
            Formatted report string
        """
        metrics = self._calculate_aggregate_metrics()
        
        report = f"""
=== EvidenceFlow AI Evaluation Report ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY
-------
Total Questions: {metrics['total_questions']}
Successful: {metrics['successful']}
Failed: {metrics['failed']}

PERFORMANCE METRICS
-------------------
Average Confidence: {metrics['avg_confidence']:.3f}
Average Latency: {metrics['avg_latency']:.3f}s
Average Iterations: {metrics['avg_iterations']:.1f}

EVIDENCE QUALITY
----------------
Average Quality: {metrics['avg_evidence_quality']:.3f}
Average Relevance: {metrics['avg_evidence_relevance']:.3f}
Average Coverage: {metrics['avg_evidence_coverage']:.3f}
Average Diversity: {metrics['avg_evidence_diversity']:.3f}

CITATION VERIFICATION
---------------------
Support Rate: {metrics['citation_support_rate']:.1%}

CACHE PERFORMANCE
-----------------
Hit Rate: {metrics['cache_hit_rate']:.1%}
"""
        
        if 'avg_answer_similarity' in metrics:
            report += f"\nANSWER SIMILARITY\n------------------\nAverage: {metrics['avg_answer_similarity']:.3f}\n"
        
        return report


class BenchmarkSuite:
    """Predefined benchmark questions for testing"""
    
    @staticmethod
    def get_benchmark_questions() -> List[str]:
        """Get standard benchmark questions"""
        return [
            "What is the main topic of the documents?",
            "How does the system work?",
            "What are the key benefits mentioned?",
            "What are the potential challenges?",
            "What recommendations are provided?",
            "What is the conclusion?",
            "What data or statistics are presented?",
            "Who are the main stakeholders?",
            "What is the timeline mentioned?",
            "What are the technical requirements?"
        ]
    
    @staticmethod
    def get_domain_specific_questions(domain: str) -> List[str]:
        """
        Get domain-specific questions
        
        Args:
            domain: Domain name (e.g., 'medical', 'legal', 'technical')
            
        Returns:
            List of domain-specific questions
        """
        domain_questions = {
            'medical': [
                "What are the symptoms described?",
                "What treatments are recommended?",
                "What are the potential side effects?",
                "What is the prognosis?",
                "What preventive measures are suggested?"
            ],
            'legal': [
                "What are the key legal provisions?",
                "What are the penalties mentioned?",
                "What precedents are cited?",
                "What are the contractual obligations?",
                "What jurisdiction applies?"
            ],
            'technical': [
                "What is the system architecture?",
                "What technologies are used?",
                "What are the performance requirements?",
                "What security measures are implemented?",
                "What are the integration points?"
            ]
        }
        
        return domain_questions.get(domain.lower(), BenchmarkSuite.get_benchmark_questions())
