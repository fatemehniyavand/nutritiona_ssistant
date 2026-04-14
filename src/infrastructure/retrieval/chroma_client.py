import chromadb
from src.infrastructure.config.settings import settings


class ChromaClientFactory:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = chromadb.PersistentClient(path=settings.chroma_path)
        return cls._client

    @classmethod
    def get_or_create_collection(cls, name: str):
        client = cls.get_client()
        return client.get_or_create_collection(name=name)