import hashlib
import io

import faiss
from llama_index import ServiceContext, StorageContext, VectorStoreIndex
from llama_index.node_parser import SentenceSplitter
from llama_index.schema import Document
from llama_index.vector_stores import FaissVectorStore
from pypdf import PdfReader

from src.helpers import get_chat_model
from src.insight_themes import THEMES


def pdf_fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_retriever(pdf_bytes: bytes, api_key: str, top_k: int = 4):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    docs = []
    for page_no, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            docs.append(Document(text=text, metadata={"page": page_no}))
    if not docs:
        raise ValueError("No text could be read from the PDF.")

    nodes = SentenceSplitter(chunk_size=1024, chunk_overlap=128).get_nodes_from_documents(docs)
    llm = get_chat_model(api_key)
    store = FaissVectorStore(faiss_index=faiss.IndexFlatL2(1536))
    ctx = ServiceContext.from_defaults(llm=llm)
    index = VectorStoreIndex(
        nodes,
        service_context=ctx,
        storage_context=StorageContext.from_defaults(vector_store=store),
    )
    return index.as_retriever(similarity_top_k=top_k)


def retrieve_for_theme(retriever, theme_key: str, top_k: int = 4) -> list[dict]:
    theme = THEMES[theme_key]
    query = theme.get("retrieval_query") or theme["label"]
    chunks = []
    for node in retriever.retrieve(query)[:top_k]:
        text = node.get_content() if hasattr(node, "get_content") else str(node)
        chunks.append(
            {
                "text": text,
                "score": getattr(node, "score", None),
                "meta": dict(getattr(node, "metadata", {}) or {}),
            }
        )
    return chunks
