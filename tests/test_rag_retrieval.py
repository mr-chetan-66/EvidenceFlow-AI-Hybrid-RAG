import asyncio
import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from src.bm25_search import BM25Search
from src.cag_cache import CAGCache
from src.agentic_retrieval import AgenticRetrieval
from src.evidence_grader import EvidenceGrader
from src.evaluation import EvaluationSystem
from src.hybrid_retrieval import HybridRetriever
from src.vectorstore import VectorStore
from src.document_indexing import index_uploaded_chunks


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


class MutableCollection:
    def __init__(self, records):
        self.records = dict(records)

    def upsert(self, ids, documents, metadatas, embeddings):
        for document_id, document, metadata in zip(ids, documents, metadatas):
            self.records[document_id] = (document, metadata)

    def get(self, where, include):
        source = where["source"]
        matching = [
            (document_id, record)
            for document_id, record in self.records.items()
            if record[1].get("source") == source
        ]
        return {
            "ids": [document_id for document_id, _ in matching],
            "metadatas": [record[1] for _, record in matching],
        }

    def delete(self, ids):
        for document_id in ids:
            self.records.pop(document_id, None)

    def count(self):
        return len(self.records)


class RecordingEmbeddingManager:
    def __init__(self):
        self.texts = None

    def genetate_embedding(self, texts, progress_callback=None):
        self.texts = list(texts)
        return np.ones((len(texts), 2), dtype=np.float32)


class RecordingCache:
    def __init__(self):
        self.invalidated = False

    def invalidate(self):
        self.invalidated = True


class FakeAgenticRetrieval:
    def __init__(self, hybrid_retriever, **kwargs):
        self.hybrid_retriever = hybrid_retriever


def write_test_pdf(path, text):
    path.write_bytes(create_test_pdf_bytes(text))


def create_test_pdf_bytes(text):
    import fitz

    pdf = fitz.open()
    page = pdf.new_page()
    if text:
        page.insert_text((72, 72), text)
    content = pdf.tobytes()
    pdf.close()
    return content


def create_ephemeral_vectorstore():
    import chromadb

    vectorstore = VectorStore.__new__(VectorStore)
    vectorstore.collection_name = "pdf_documents"
    vectorstore.client = chromadb.EphemeralClient()
    vectorstore.collection = vectorstore.client.get_or_create_collection(
        name=vectorstore.collection_name,
    )
    return vectorstore


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

    def test_upload_embeds_only_new_chunks_and_replaces_only_matching_source(self):
        source = "/persistent/pdf/new.pdf"
        collection = MutableCollection({
            "stale-chunk": ("old text", {"source": source, "page": 1}),
            "other-document": ("keep this", {"source": "/persistent/pdf/other.pdf", "page": 1}),
        })
        vectorstore = VectorStore.__new__(VectorStore)
        vectorstore.collection = collection
        vectorstore.collection_name = "pdf_documents"
        embedding_manager = RecordingEmbeddingManager()
        chunk = SimpleNamespace(
            page_content="new uploaded text",
            metadata={"source": source, "page": 1},
        )

        index_uploaded_chunks([chunk], embedding_manager, vectorstore)

        self.assertEqual(embedding_manager.texts, ["new uploaded text"])
        self.assertEqual(collection.count(), 2)
        self.assertEqual(
            {record[1]["source"] for record in collection.records.values()},
            {source, "/persistent/pdf/other.pdf"},
        )
        self.assertNotIn("stale-chunk", collection.records)

    def test_backend_upload_replaces_selected_sources_and_refreshes_full_bm25(self):
        from backend import app as backend_app

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf_directory = root / "pdf"
            pdf_directory.mkdir()
            uploaded_paths = [pdf_directory / "new.pdf", pdf_directory / "second.pdf"]
            write_test_pdf(uploaded_paths[0], "New upload contains a blue whale reference.")
            write_test_pdf(uploaded_paths[1], "Second upload contains a red maple reference.")

            vectorstore = create_ephemeral_vectorstore()
            previous_chunks = [
                SimpleNamespace(
                    page_content="Old version of uploaded source.",
                    metadata={"source": str(uploaded_paths[0]), "page": 0},
                ),
                SimpleNamespace(
                    page_content="Unrelated document must remain indexed.",
                    metadata={"source": str(pdf_directory / "other.pdf"), "page": 0},
                ),
            ]
            vectorstore.add_documents(
                previous_chunks,
                np.ones((len(previous_chunks), 2), dtype=np.float32),
            )
            embedding_manager = RecordingEmbeddingManager()
            existing_cache = RecordingCache()
            replacement_cache = RecordingCache()
            updated_retriever = None
            updated_cache = None

            with (
                patch.object(backend_app, "get_pdf_directory", return_value=pdf_directory),
                patch.object(backend_app, "embedding_manager", embedding_manager),
                patch.object(backend_app, "vectorstore", vectorstore),
                patch.object(backend_app, "hybrid_retriever", None),
                patch.object(backend_app, "agentic_retrieval", None),
                patch.object(backend_app, "cache", existing_cache),
                patch.object(backend_app, "system_ready", False),
                patch.object(backend_app, "AgenticRetrieval", FakeAgenticRetrieval),
                patch.object(backend_app, "CAGCache", side_effect=lambda **kwargs: replacement_cache),
                patch.object(backend_app, "report_indexing_progress"),
            ):
                result = backend_app.index_uploaded_documents(["new.pdf", "second.pdf"])
                first_ids = set(vectorstore.get_all_documents()[2])
                first_count = vectorstore.collection.count()
                repeated_result = backend_app.index_uploaded_documents(
                    ["new.pdf", "second.pdf"]
                )
                updated_retriever = backend_app.hybrid_retriever
                updated_cache = backend_app.cache

            documents, metadatas, _ = vectorstore.get_all_documents()
            indexed_sources = {metadata["source"] for metadata in metadatas}
            indexed_text = " ".join(documents)

        self.assertEqual(result["document_count"], 2)
        self.assertEqual(repeated_result["document_count"], 2)
        self.assertEqual(indexed_sources, {
            str(uploaded_paths[0]),
            str(uploaded_paths[1]),
            str(pdf_directory / "other.pdf"),
        })
        self.assertIn("blue whale", indexed_text)
        self.assertIn("red maple", indexed_text)
        self.assertIn("Unrelated document", indexed_text)
        self.assertNotIn("Old version", indexed_text)
        self.assertEqual(len(embedding_manager.texts), 2)
        self.assertTrue(all("Old version" not in text for text in embedding_manager.texts))
        self.assertEqual(vectorstore.collection.count(), first_count)
        self.assertEqual(set(vectorstore.get_all_documents()[2]), first_ids)
        self.assertEqual(
            len(updated_retriever.bm25.documents),
            len(documents),
        )
        self.assertTrue(existing_cache.invalidated)
        self.assertIs(updated_cache, replacement_cache)

    def test_unindexable_upload_batch_does_not_mutate_vectors_or_cache(self):
        from backend import app as backend_app

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            pdf_directory = root / "pdf"
            pdf_directory.mkdir()
            valid_pdf = pdf_directory / "valid.pdf"
            empty_pdf = pdf_directory / "empty.pdf"
            write_test_pdf(valid_pdf, "This upload contains valid searchable text.")
            write_test_pdf(empty_pdf, "")

            vectorstore = create_ephemeral_vectorstore()
            original_chunk = SimpleNamespace(
                page_content="Original document must remain intact.",
                metadata={"source": str(empty_pdf), "page": 0},
            )
            vectorstore.add_documents(
                [original_chunk],
                np.ones((1, 2), dtype=np.float32),
            )
            original_ids = set(vectorstore.get_all_documents()[2])
            embedding_manager = RecordingEmbeddingManager()
            existing_cache = RecordingCache()

            with (
                patch.object(backend_app, "get_pdf_directory", return_value=pdf_directory),
                patch.object(backend_app, "embedding_manager", embedding_manager),
                patch.object(backend_app, "vectorstore", vectorstore),
                patch.object(backend_app, "cache", existing_cache),
                patch.object(backend_app, "report_indexing_progress"),
            ):
                with self.assertRaisesRegex(ValueError, "empty.pdf"):
                    backend_app.index_uploaded_documents(["valid.pdf", "empty.pdf"])

            self.assertEqual(set(vectorstore.get_all_documents()[2]), original_ids)
            self.assertTrue(any(
                "Original document" in document
                for document in vectorstore.get_all_documents()[0]
            ))
            self.assertIsNone(embedding_manager.texts)
            self.assertFalse(existing_cache.invalidated)

    def test_upload_route_dispatches_only_selected_files_to_incremental_indexer(self):
        from backend import app as backend_app
        import httpx

        with tempfile.TemporaryDirectory() as temporary_directory:
            pdf_directory = Path(temporary_directory)
            pdf_content = create_test_pdf_bytes("Route upload selected document.")
            second_pdf_content = create_test_pdf_bytes("Second route-upload document.")
            scheduled_operations = []

            async def fake_run_tracked_rebuild(operation, uploaded_filenames=None):
                scheduled_operations.append((operation, uploaded_filenames))

            async def make_upload_request():
                transport = httpx.ASGITransport(app=backend_app.app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    response = await client.post(
                        "/admin/upload",
                        files=[
                            ("files", ("selected.pdf", pdf_content, "application/pdf")),
                            ("files", ("second.pdf", second_pdf_content, "application/pdf")),
                        ],
                    )
                    await backend_app.background_indexing_task
                    return response

            previous_overrides = backend_app.app.dependency_overrides.copy()
            backend_app.app.dependency_overrides[backend_app.require_admin] = (
                lambda: SimpleNamespace()
            )
            try:
                with (
                    patch.object(backend_app, "get_pdf_directory", return_value=pdf_directory),
                    patch.object(backend_app, "start_indexing_operation", return_value=True),
                    patch.object(backend_app, "report_indexing_progress"),
                    patch.object(backend_app, "run_tracked_rebuild", fake_run_tracked_rebuild),
                    patch.object(backend_app, "background_indexing_task", None),
                ):
                    response = asyncio.run(make_upload_request())
            finally:
                backend_app.app.dependency_overrides.clear()
                backend_app.app.dependency_overrides.update(previous_overrides)

            self.assertEqual((pdf_directory / "selected.pdf").read_bytes(), pdf_content)
            self.assertEqual((pdf_directory / "second.pdf").read_bytes(), second_pdf_content)

        self.assertEqual(response.status_code, 200)
        uploaded_files = ["selected.pdf", "second.pdf"]
        self.assertEqual(response.json()["uploaded_files"], uploaded_files)
        self.assertEqual(scheduled_operations, [("upload", uploaded_files)])

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