"""Adaptive text chunking utilities shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Chunk:
    """Representation of a single text chunk."""

    text: str
    index: int
    start: int
    end: int

    @property
    def length(self) -> int:
        """Return the number of characters in the chunk."""

        return len(self.text)


class AdaptiveTextChunker:
    """Create overlapping text chunks with adaptive window sizes."""

    def __init__(
        self,
        *,
        base_chunk_size: int = 1200,
        chunk_overlap: int = 200,
        max_chunk_size: int = 2400,
        large_document_threshold: int = 60_000,
        target_chunk_count: int = 256,
        min_chunk_size: int = 400,
        strategy_name: str = "adaptive-paragraph",
    ) -> None:
        if base_chunk_size <= 0:
            raise ValueError("base_chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must not be negative")
        if max_chunk_size < base_chunk_size:
            raise ValueError("max_chunk_size must be >= base_chunk_size")

        self.base_chunk_size = base_chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_chunk_size = max_chunk_size
        self.large_document_threshold = large_document_threshold
        self.target_chunk_count = max(1, target_chunk_count)
        self.min_chunk_size = max(1, min_chunk_size)
        self.strategy_name = strategy_name

    # ------------------------------------------------------------------
    def chunk(self, text: str) -> List[Chunk]:
        """Split ``text`` into overlapping chunks with adaptive sizing."""

        normalized = text.replace("\r\n", "\n")
        if not normalized.strip():
            return []

        chunk_size = self._determine_chunk_size(len(normalized))
        overlap = min(self.chunk_overlap, max(0, chunk_size // 3))

        start = 0
        index = 0
        chunks: List[Chunk] = []
        length = len(normalized)

        while start < length:
            window_end = min(length, start + chunk_size)
            split_end = self._find_split_point(normalized, start, window_end)
            raw_chunk = normalized[start:split_end]
            stripped_chunk = raw_chunk.strip("\n")
            leading_ws = len(raw_chunk) - len(raw_chunk.lstrip("\n"))
            trailing_ws = len(raw_chunk) - len(raw_chunk.rstrip("\n"))
            chunk_start = start + leading_ws
            chunk_end = split_end - trailing_ws

            if chunk_end < chunk_start:
                chunk_end = split_end
                chunk_start = start
                stripped_chunk = raw_chunk.strip()

            stripped_chunk = stripped_chunk.strip()
            if stripped_chunk:
                relative_start = raw_chunk.find(stripped_chunk)
                if relative_start != -1:
                    chunk_start = start + relative_start
                    chunk_end = chunk_start + len(stripped_chunk)

                chunks.append(Chunk(text=stripped_chunk, index=index, start=chunk_start, end=chunk_end))
                index += 1

            if split_end >= length:
                break

            next_start = max(chunk_end - overlap, split_end - overlap)
            if next_start <= start:
                next_start = split_end
            start = next_start

        return chunks

    # ------------------------------------------------------------------
    def _determine_chunk_size(self, document_length: int) -> int:
        if document_length < self.large_document_threshold:
            return self.base_chunk_size

        suggested = max(
            self.base_chunk_size,
            min(self.max_chunk_size, int(document_length / self.target_chunk_count)),
        )
        return min(self.max_chunk_size, max(self.base_chunk_size, suggested))

    def _find_split_point(self, text: str, start: int, window_end: int) -> int:
        preferred = ["\n\n", "\n", ". ", ".", " "]
        for token in preferred:
            pos = text.rfind(token, start, window_end)
            if pos != -1 and pos - start >= self.min_chunk_size:
                return pos + len(token)
        return window_end


__all__ = ["AdaptiveTextChunker", "Chunk"]
