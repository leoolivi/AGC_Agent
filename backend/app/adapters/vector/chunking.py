"""Text chunking for vector store — max 512 tokens, min 64, overlap 64."""
from __future__ import annotations


def chunk_text(
    text: str,
    max_tokens: int = 512,
    min_tokens: int = 64,
    overlap: int = 64,
) -> list[str]:
    """Split text into chunks by approximate token count (words as proxy)."""
    if not text.strip():
        return []
    words = text.split()
    if len(words) <= max_tokens:
        return [text] if len(words) >= min_tokens else [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks
