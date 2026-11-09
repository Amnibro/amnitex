"""atex: a lossless byte-page memory layer for MCP-capable AI coding assistants."""
from atex.kb import KnowledgeBase, KnowledgeBaseError
from atex.retriever import KBRetriever
__version__ = "0.3.6"
__all__ = ["KnowledgeBase", "KnowledgeBaseError", "KBRetriever", "__version__"]
