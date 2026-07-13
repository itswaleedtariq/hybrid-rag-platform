from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "HybridDocs AI"
    debug: bool = True
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = 1200
    jwt_secret_key: str = "change-this-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    database_url: str = "sqlite:///./data/rag_platform.db"
    chroma_path: Path = Path("./chroma_db")
    upload_path: Path = Path("./uploads")
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_mb: int = 20
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    enable_reranker: bool = True
    chunk_size: int = 800
    chunk_overlap: int = 120
    semantic_break_threshold: float = 0.55
    dense_weight: float = 0.6
    bm25_weight: float = 0.4
    rrf_k: int = 60
    retrieval_candidates: int = 20
    default_top_k: int = 5
    min_retrieval_confidence: float = 0.30
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)
    @property
    def origins(self): return [x.strip() for x in self.cors_origins.split(',') if x.strip()]
    @property
    def max_upload_bytes(self): return self.max_upload_mb * 1024 * 1024
    def prepare(self):
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.upload_path.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith('sqlite:///'):
            Path(self.database_url.replace('sqlite:///','',1)).parent.mkdir(parents=True, exist_ok=True)

@lru_cache
def get_settings():
    s=Settings(); s.prepare(); return s
settings=get_settings()
