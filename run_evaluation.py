"""
Evaluation Script
Run comprehensive evaluation of EvidenceFlow AI system
"""
from src.load_and_chunk import process_all_pdfs, chunk_documnents
from src.embedding import EmbeddingManager
from src.vectorstore import VectorStore
from src.hybrid_retrieval import HybridRetriever
from src.agentic_retrieval import AgenticRetrieval
from src.evaluation import EvaluationSystem, BenchmarkSuite


def main():
    """Main evaluation function"""
    print("=== EvidenceFlow AI Evaluation ===\n")
    
    # Initialize system
    print("Initializing system...")
    
    # Load documents
    print("Loading documents...")
    all_documents = process_all_pdfs("./data")
    print(f"Loaded {len(all_documents)} documents")
    
    # Chunk documents
    print("Chunking documents...")
    all_chunks = chunk_documnents(all_documents)
    print(f"Created {len(all_chunks)} chunks")
    
    # Initialize components
    print("Initializing AI components...")
    embedding_manager = EmbeddingManager()
    vectorstore = VectorStore()
    
    # Generate embeddings
    texts = [doc.page_content for doc in all_chunks]
    embeddings = embedding_manager.genetate_embedding(texts)
    
    # Store in vector store
    vectorstore.add_documents(all_chunks, embeddings)
    
    # Initialize hybrid retriever
    hybrid_retriever = HybridRetriever(embedding_manager, vectorstore)
    hybrid_retriever.index_documents(texts)
    
    # Initialize agentic retrieval
    agentic_retrieval = AgenticRetrieval(hybrid_retriever)
    
    print("System initialized!\n")
    
    # Get benchmark questions
    print("Loading benchmark questions...")
    questions = BenchmarkSuite.get_benchmark_questions()
    print(f"Loaded {len(questions)} benchmark questions\n")
    
    # Run evaluation
    print("Running evaluation...")
    evaluation_system = EvaluationSystem(agentic_retrieval)
    results = evaluation_system.run_evaluation(questions)
    
    # Display results
    print("\n=== Evaluation Results ===")
    print(evaluation_system.generate_report())
    
    # Save results
    timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"./data/evaluation_results_{timestamp}.json"
    evaluation_system.save_results(results_file)
    print(f"\nResults saved to {results_file}")
    
    # Display detailed results
    print("\n=== Detailed Results ===")
    df = evaluation_system.get_results_dataframe()
    print(df[['question', 'confidence', 'latency', 'evidence_quality', 'citation_supported']].to_string())


if __name__ == "__main__":
    main()
