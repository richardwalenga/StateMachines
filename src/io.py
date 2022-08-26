import functools
import io
from typing import Iterable

def each_character_of(to_read: io.TextIOBase) -> Iterable[str]:
    """Reads one character at a time from a text stream

    Args:
        to_read (io.TextIOBase): The stream of text to read.

    Returns:
        Iterable[str]: Each character read.
    """
    return iter(functools.partial(to_read.read, 1), '')