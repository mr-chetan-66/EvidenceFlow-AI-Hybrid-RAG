import numpy as np
import chromadb
import hashlib
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
            self.model=SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Error Model loading {self.model_name} : {e}")
            raise
        
    def genetate_embedding(self, text:List[str])->np.ndarray:
        if not self.model:
            raise ValueError("Model Not Loaded")
        
        embedding=self.model.encode(text,show_progress_bar=False)
        return embedding

    