"""Custom exceptions for the application"""


class VectorStoreError(Exception):
    """Exception raised for vector store operations"""
    pass


class EmbeddingError(Exception):
    """Exception raised for embedding generation failures"""
    pass


class CollectionError(Exception):
    """Exception raised for collection operations"""
    pass
