import tempfile
import unittest
import json
from pathlib import Path

import numpy as np

from src.bm25_search import BM25Search
from src.cag_cache import CAGCache
from src.agentic_retrieval import AgenticRetrieval
from src.evidence_grader import EvidenceGrader
from src.evaluation import EvaluationSystem
from src.hybrid_retrieval import HybridRetriever
from src.vectorstore import VectorStore


class FakeEmbeddingManager:
    def genetate_embedding(self, texts, progress_callback=None):
        return np.ones((len(texts), 2), dtype=np.float32)


class FakeVectorStore:
    def __init__(self, documents, metadatas, ids, distances):
        self.documents = documents
        self.metadatas = metadatas
        self.ids = ids
        self.distances = distances

    def similar_search(self, query_embedding, n_results=5):
        return {
            "documents": [self.documents[:n_results]],
            "metadatas": [self.metadatas[:n_results]],
            "ids": [self.ids[:n_results]],
            "distances": [self.distances[:n_results]],
        }


class FakeCachedEmbeddingManager:
    def genetate_embedding(self, texts):
        return np.ones((len(texts), 2), dtype=np.float32)


class NoEmbeddingManager:
    def genetate_embedding(self, texts):
        raise AssertionError("Exact-query caching must not run another embedding pass")


class PagedCollection:
    def __init__(self, records):
        self.records = records

    def count(self):
        return len(self.records)

    def get(self, limit, offset, include):
        page = self.records[offset:offset + limit]
        return {
            "documents": [record[0] for record in page],
            "metadatas": [record[1] for record in page],
            "ids": [record[2] for record in page],
        }


class EmptyRetriever:
    def retrieve(self, query, k, alpha):
        return [], {"query": query, "bm25_count": 0, "vector_count": 0}


class NoCallLLM:
    def __init__(self):
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        raise AssertionError("LLM must not be called without retrieved evidence")


class RecordingLLM:
    def __init__(self):
        self.prompt = None

    def invoke(self, prompt):
        self.prompt = prompt
        return type("Response", (), {"content": "Amazon S3 is object storage [0]."})()


class HybridRetrievalTests(unittest.TestCase):
    def test_bm25_ignores_question_stopwords(self):
        self.assertEqual(BM25Search.tokenize("what is AWS S3?"), ["aws", "s3"])

    def test_dense_result_can_win_and_keeps_citation_metadata(self):
        documents = [
            "What is normalization? Database normalization removes redundant records.",
            "Amazon S3 is an object storage service for buckets and objects.",
        ]
        metadatas = [
            {"source": "database.pdf", "page": 4},
            {"source": "aws-overview.pdf", "page": 141},
        ]
        ids = ["database-4", "aws-s3-141"]
        store = FakeVectorStore(
            documents=[documents[1]],
            metadatas=[metadatas[1]],
            ids=[ids[1]],
            distances=[0.2],
        )
        retriever = HybridRetriever(FakeEmbeddingManager(), store)
        retriever.index_documents(documents, metadatas, ids)

        results, _ = retriever.retrieve("what is AWS S3", k=2, alpha=0.5)

        self.assertEqual(results[0]["document"], documents[1])
        self.assertEqual(results[0]["metadata"], metadatas[1])
        self.assertEqual(results[0]["id"], ids[1])

    def test_default_weighting_prefers_dense_definition_over_keyword_catalog(self):
        documents = [
            "AWS AWS AWS service catalog with developer tools and service topics.",
            "Amazon Web Services provides a reliable cloud infrastructure platform.",
        ]
        metadatas = [
            {"source": "service-catalog.pdf", "page": 60},
            {"source": "aws-overview.pdf", "page": 10},
        ]
        ids = ["catalog", "definition"]
        store = FakeVectorStore(
            documents=[documents[1]],
            metadatas=[metadatas[1]],
            ids=[ids[1]],
            distances=[0.4],
        )
        retriever = HybridRetriever(FakeEmbeddingManager(), store)
        retriever.index_documents(documents, metadatas, ids)

        results, _ = retriever.retrieve("what is AWS", k=2)

        self.assertEqual(results[0]["id"], "definition")

    def test_zero_signal_vector_neighbors_are_not_returned_as_evidence(self):
        document = "Agriculture uses irrigation to improve crop yields."
        store = FakeVectorStore(
            documents=[document],
            metadatas=[{"source": "agriculture.pdf", "page": 1}],
            ids=["agriculture-1"],
            distances=[1.2],
        )
        retriever = HybridRetriever(FakeEmbeddingManager(), store)
        retriever.index_documents([document], [{"source": "agriculture.pdf", "page": 1}], ["agriculture-1"])

        results, _ = retriever.retrieve("what is AWS S3", k=1, alpha=0.5)

        self.assertEqual(results, [])

    def test_semantic_cache_does_not_answer_a_different_question(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = CAGCache(
                cache_dir=cache_dir,
                embedding_manager=FakeCachedEmbeddingManager(),
            )
            cache.cache_data["queries"]["unrelated-key"] = {
                "query": "what is aws",
                "query_embedding": [1.0, 1.0],
                "response": "Cached general AWS answer",
                "evidence": [],
                "metadata": {},
            }

            result = cache.get("what is AWS S3")

        self.assertIsNone(result)

    def test_exact_cache_write_does_not_embed_question_again(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            cache = CAGCache(cache_dir=cache_dir, embedding_manager=NoEmbeddingManager())
            cache.set("what is AWS", "Grounded answer", evidence=[])
            result = cache.get("what is AWS")

        self.assertEqual(result["response"], "Grounded answer")
        self.assertNotIn("query_embedding", result)

    def test_old_cache_version_is_discarded(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            cache_path = Path(cache_dir) / "cache.json"
            cache_path.write_text(json.dumps({
                "queries": {"old": {"response": "stale answer"}},
                "metadata": {"version": "1.0"},
            }), encoding="utf-8")
            cache = CAGCache(
                cache_dir=cache_dir,
                embedding_manager=FakeCachedEmbeddingManager(),
            )

        self.assertEqual(cache.cache_data["queries"], {})
        self.assertEqual(cache.cache_data["metadata"]["version"], CAGCache.CACHE_VERSION)

    def test_chroma_restore_reads_all_pages_with_metadata(self):
        store = VectorStore.__new__(VectorStore)
        store.collection = PagedCollection([
            (f"chunk {index}", {"source": f"doc-{index}.pdf", "page": index}, f"id-{index}")
            for index in range(5)
        ])

        documents, metadatas, ids = store.get_all_documents(batch_size=2)

        self.assertEqual(len(documents), 5)
        self.assertEqual(metadatas[4]["source"], "doc-4.pdf")
        self.assertEqual(ids, [f"id-{index}" for index in range(5)])

    def test_no_evidence_skips_answer_model(self):
        agent = AgenticRetrieval.__new__(AgenticRetrieval)
        agent.cache = None
        agent.max_iterations = 2
        agent.hybrid_retriever = EmptyRetriever()
        agent.evidence_grader = EvidenceGrader()
        agent.enable_reranking = False
        agent.reranker = None
        agent.enable_citation_check = False
        agent.citation_verifier = None
        agent.llm = NoCallLLM()

        result = agent.retrieve_and_answer("What is an undocumented service?")

        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["evidence"], [])
        self.assertIn("could not find relevant evidence", result["answer"].lower())
        self.assertEqual(agent.llm.calls, 0)

    def test_answer_context_includes_source_and_page(self):
        agent = AgenticRetrieval.__new__(AgenticRetrieval)
        agent.llm = RecordingLLM()
        answer = agent._generate_answer("What is S3?", [{
            "document": "Amazon S3 is an object storage service.",
            "metadata": {"source": "/persistent/pdf/aws-overview.pdf", "page": 141},
        }])

        self.assertIn("aws-overview.pdf", agent.llm.prompt)
        self.assertIn("141", agent.llm.prompt)
        self.assertTrue(answer)

    def test_disabled_citation_verification_reports_na(self):
        evaluation = EvaluationSystem.__new__(EvaluationSystem)
        evaluation.results = [{
            "question": "What is S3?",
            "confidence": 0.7,
            "latency": 0.2,
            "iterations": 1,
            "evidence_quality": 0.8,
            "evidence_relevance": 0.9,
            "evidence_coverage": 0.7,
            "evidence_diversity": 0.5,
            "citation_supported": None,
            "cache_hit": "miss",
        }]

        metrics = evaluation._calculate_aggregate_metrics()
        report = evaluation.generate_report()

        self.assertEqual(metrics["citation_verification_rate"], 0.0)
        self.assertIsNone(metrics["citation_support_rate"])
        self.assertIn("N/A (verification disabled)", report)


if __name__ == "__main__":
    unittest.main()