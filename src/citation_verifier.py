"""
Citation Verification Module
Verifies that generated claims are supported by retrieved evidence
"""
from typing import List, Dict, Any, Tuple
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


class CitationVerifier:
    def __init__(self):
        """Initialize citation verifier with LLM"""
        self.llm = ChatGroq(
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="openai/gpt-oss-20b",
            temperature=0.1,
            max_tokens=512
        )
        
    def verify_citations(
        self, 
        answer: str, 
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verify that the answer is supported by the evidence
        
        Args:
            answer: Generated answer
            evidence: Retrieved evidence documents
            
        Returns:
            Dictionary with verification results
        """
        if not evidence:
            return {
                'is_supported': False,
                'confidence': 0.0,
                'unsupported_claims': [],
                'verification_details': "No evidence provided for verification"
            }
        
        # Prepare evidence text
        evidence_text = "\n\n".join([
            f"[{i}] {doc['document']}"
            for i, doc in enumerate(evidence)
        ])
        
        # Create verification prompt
        verification_prompt = f"""
You are a citation verification system. Your task is to verify if the given answer is supported by the provided evidence.

Answer:
{answer}

Evidence:
{evidence_text}

Instructions:
1. Analyze the answer and identify key claims
2. Check if each claim is supported by the evidence
3. Return a JSON-like response with:
   - is_supported: true/false
   - confidence: 0.0-1.0
   - unsupported_claims: list of claims not supported
   - verification_details: brief explanation

Format your response as:
IS_SUPPORTED: [true/false]
CONFIDENCE: [0.0-1.0]
UNSUPPORTED_CLAIMS: [claim1, claim2, ...]
VERIFICATION_DETAILS: [explanation]
"""
        
        try:
            response = self.llm.invoke(verification_prompt)
            result = self._parse_verification_response(response.content)
            
            # Add citation metadata
            result['evidence_count'] = len(evidence)
            result['citations'] = self._extract_citations(evidence)
            
            return result
            
        except Exception as e:
            print(f"Citation verification error: {e}")
            return {
                'is_supported': False,
                'confidence': 0.0,
                'unsupported_claims': [],
                'verification_details': f"Verification failed: {str(e)}",
                'evidence_count': len(evidence),
                'citations': self._extract_citations(evidence)
            }
    
    def _parse_verification_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM verification response
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed verification results
        """
        result = {
            'is_supported': False,
            'confidence': 0.0,
            'unsupported_claims': [],
            'verification_details': ''
        }
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('IS_SUPPORTED:'):
                result['is_supported'] = 'true' in line.lower()
            elif line.startswith('CONFIDENCE:'):
                try:
                    result['confidence'] = float(line.split(':')[1].strip())
                except:
                    result['confidence'] = 0.5
            elif line.startswith('UNSUPPORTED_CLAIMS:'):
                claims_str = line.split(':', 1)[1].strip()
                if claims_str and claims_str != '[]':
                    # Parse list-like string
                    claims_str = claims_str.strip('[]')
                    result['unsupported_claims'] = [
                        c.strip().strip('"').strip("'")
                        for c in claims_str.split(',')
                        if c.strip()
                    ]
            elif line.startswith('VERIFICATION_DETAILS:'):
                result['verification_details'] = line.split(':', 1)[1].strip()
        
        return result
    
    def _extract_citations(self, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract citation information from evidence
        
        Args:
            evidence: Retrieved evidence documents
            
        Returns:
            List of citation information
        """
        citations = []
        for i, doc in enumerate(evidence):
            metadata = doc.get('metadata', {})
            citation = {
                'index': i,
                'source': metadata.get('source', 'unknown'),
                'page': metadata.get('page', 'N/A'),
                'score': doc.get('combined_score', doc.get('score', 0.0)),
                'text': doc.get('document', '')[:200] + '...'  # Preview
            }
            citations.append(citation)
        
        return citations
    
    def format_answer_with_citations(
        self, 
        answer: str, 
        citations: List[Dict[str, Any]]
    ) -> str:
        """
        Format answer with citation markers
        
        Args:
            answer: Original answer
            citations: Citation information
            
        Returns:
            Formatted answer with citations
        """
        if not citations:
            return answer
        
        # Add citation references to the answer
        citation_text = "\n\n**Sources:**\n"
        for i, citation in enumerate(citations):
            source_name = citation['source'].split('/')[-1]
            citation_text += f"[{i}] {source_name} (Page {citation['page']})\n"
        
        return answer + citation_text
