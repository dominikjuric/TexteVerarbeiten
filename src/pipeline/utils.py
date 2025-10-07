"""Utility helpers shared across pipeline modules."""

from __future__ import annotations

from itertools import islice
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, TypeVar


T = TypeVar("T")


def batched(iterable: Sequence[T] | Iterable[T], size: int) -> Iterator[List[T]]:
    """Yield successive batches from ``iterable`` with ``size`` elements."""

    if size <= 0:
        raise ValueError("batch size must be greater than zero")

    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


def ensure_directory(path: Path) -> Path:
    """Create ``path`` (and parents) if necessary and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path

