from __future__ import annotations
from contextlib import AbstractContextManager
import io


class StringBuilder(AbstractContextManager):
    """This class provides a means to incrementally build a string.
    Use with the with statement to ensure proper resource disposal.

    Usage:
        with StringBuilder() as sb:
            sb.append('A string').append('and another')
            print(str(sb)) # Outputs: A string and another
    """
    __slots__ = ('string_io',)

    def __init__(self, initial_value: str = None) -> None:
        """Constructor

        Args:
            initial_value (str, optional): The first string value to store. Defaults to None.
        """
        self.string_io = io.StringIO(initial_value=initial_value)

    def __enter__(self) -> StringBuilder:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.string_io.__exit__(exc_type, exc_value, traceback)

    def __len__(self) -> int:
        """Returns the number of characters appended so far.

        Returns:
            int: The number of characters.
        """
        return self.string_io.tell()

    def __str__(self) -> str:
        """Returns the builder contents as a string.

        Returns:
            str: The complete string.
        """
        self.string_io.truncate()
        return self.string_io.getvalue()

    def append(self, to_append: str) -> StringBuilder:
        """Appends the given string.

        Args:
            to_append (str): The string to append.

        Returns:
            StringBuilder: The current instance.
        """
        self.string_io.write(to_append)
        return self

    def build(self) -> str:
        """Returns the builder contents as a string.

        Returns:
            str: The complete string.
        """
        return str(self)

    def clear(self) -> StringBuilder:
        """Clears what has already been appended.

        Returns:
            StringBuilder: The current instance.
        """
        self.string_io.seek(0)
        return self
