import numpy as np
import chromadb
import hashlib
import math
from chromadb.config import Settings
from typing import List, Dict, Tuple, Any
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class EmbeddingManager:
    def __init__(self, model_name="all-MiniLM-L6-V2"):
        self.model_name=model_name
        self.model=None
        self._load_model()
        
    def _load_model(self):
        try:
            # Load model with optimized settings
            self.model=SentenceTransformer(
                self.model_name,
                device='cpu'  # Force CPU for consistency
            )
        except Exception as e:
            print(f"Error Model loading {self.model_name} : {e}")
            raise
        
    def _load_model(self):
        try:
            self.model=SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Error Model loading {self.model_name} : {e}")
            raise
        
    def genetate_embedding(self, text:List[str], progress_callback=None)->np.ndarray:
        if not self.model:
            raise ValueError("Model Not Loaded")

        batch_size = 32
        total_batches = math.ceil(len(text) / batch_size)
        embedding_batches = []
        for batch_index, start in enumerate(range(0, len(text), batch_size), start=1):
            embedding_batches.append(self.model.encode(
                text[start:start + batch_size],
                show_progress_bar=False,
                batch_size=batch_size,
                normalize_embeddings=True,
            ))
            if progress_callback:
                progress_callback(batch_index, total_batches)

        if not embedding_batches:
            return np.empty((0, 0), dtype=np.float32)
        return np.concatenate(embedding_batches, axis=0)

    