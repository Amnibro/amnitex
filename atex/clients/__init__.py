"""atex.clients: drive a local open-source model against an atex KB. Model-agnostic — adapters provide a chat callable."""
from atex.clients.rag import AtexRagClient
from atex.clients.ollama import make_ollama_chat,check_ollama_available
from atex.clients.validate import run_validation_loop,ValidationResult
__all__=["AtexRagClient","make_ollama_chat","check_ollama_available","run_validation_loop","ValidationResult"]
