from __future__ import annotations
from collections.abc import Iterable, Sequence
from .io import each_character_of
from .state_machine import StateMachineBase
from .string_builder import StringBuilder
import enum
import io


class States(enum.Enum):
    BEGIN = enum.auto()
    IN_FIELD = enum.auto()
    QUOTE_IN_FIELD = enum.auto()
    END_OF_FIELD = enum.auto()
    END_OF_RECORD = enum.auto()
    END = enum.auto()


class CsvParseException(Exception):
    pass


class CsvParser(StateMachineBase):
    """This is a class to parse CSV input, which can have commas, newlines
    and double quotes in a field if and only if the field starts and ends
    with double quotes; however, not every field is required to be surrounded
    by double quotes.

    Any double quotes which are meant to be taken literally must be immediately
    preceded by one.  For example, ...,"This is a double quote: "".",...
    """
    __slots__ = ('fields', 'fields_per_record',
                 'doublequotes_in_field', 'record_number')

    states = States

    def __init__(self) -> None:
        """Constructor"""
        super().__init__()
        self.fields = []
        self.fields_per_record = None
        self.doublequotes_in_field = 0
        self.record_number = 1

    @property
    def field_number(self) -> int:
        """Gives the current field number for the current record.

        Returns:
            int: The current field number.
        """
        return len(self.fields) + 1

    @property
    def has_unbalanced_doublequotes(self) -> bool:
        """Returns true if there are an odd number of
        double quotes in the current field. This could
        indicate a literal double quote is should be
        part of the parsed field or the input is malformed.

        Returns:
            bool: True when there are an odd number of double quotes.
        """
        return self.doublequotes_in_field % 2 == 1

    def end_field(self, builder: StringBuilder) -> None:
        """Finishes the current field.

        Args:
            builder (StringBuilder): Holds field contents.
        """
        if self.doublequotes_in_field > 0:
            if self.has_unbalanced_doublequotes:
                self._raise_field_error('Unbalanced double quotes found')
            if not self.state == States.QUOTE_IN_FIELD:
                self._raise_field_error('Must end with a double quote')
            self.doublequotes_in_field = 0
        self.fields.append(str(builder))
        builder.clear()
        self.transition(States.END_OF_FIELD)

    def _check_for_invalid_number_of_fields(self) -> None:
        """Ensures the number of fields is consistent for each
        record found in the csv input.

        Raises:
            CsvParseException: Raised when subsequent records
            don't have the same number of fields as the first.
        """
        num_fields = len(self.fields)
        fields_discrepancy = num_fields % self.fields_per_record
        if fields_discrepancy == 0:
            return
        problem_record_number = self.record_number - 1
        raise CsvParseException(
            f'Record {problem_record_number} has {num_fields} fields but should have {self.fields_per_record}')

    def end_record(self, builder: StringBuilder) -> None:
        """Finishes the current record.

        Args:
            builder (StringBuilder): Holds field contents.
        """
        self.end_field(builder)
        self.transition(States.END_OF_RECORD)
        self.record_number += 1
        # After the first unembedded newline is processed, we
        # need to record the number of fields in this record to
        # verify against subsequent records.
        if self.fields_per_record is None:
            self.fields_per_record = len(self.fields)
            return
        self._check_for_invalid_number_of_fields()

    def process_char(self, ch: str, builder: StringBuilder) -> None:
        """Processes the next character.

        Args:
            ch (str): The character to process.
            builder (StringBuilder): Holds field content.
        """
        if self.state == States.QUOTE_IN_FIELD:
            # We most recently found a double quote which
            # was not at the very beginning of the field.
            # In most caess we have to defer until we know
            # the next non-doublequote character in order to
            # avoid outputting a double quote in a situation
            # like this which should obviously represent an
            # empty field:  ...,"",...
            if self.has_unbalanced_doublequotes:
                builder.append('"')

        if ch == ',':
            if not self.has_unbalanced_doublequotes:
                self.end_field(builder)
                return
        elif ch == '\n':
            if self.has_unbalanced_doublequotes:
                # makes multi-line fields possible
                builder.append(ch)
            else:
                self.end_record(builder)
            return

        if self.state == States.QUOTE_IN_FIELD and not self.has_unbalanced_doublequotes:
            self._raise_field_error(
                f'Unexpected character {ch} found after a double quote')

        if self.state != States.IN_FIELD:
            self.transition(States.IN_FIELD)
        builder.append(ch)

    def process_doublequote(self, builder: StringBuilder) -> None:
        """Handles a double quote.

        Args:
            builder (StringBuilder): Holds field content.

        Raises:
            CsvParseException: Raised if a double quote is not
            found at the very beginning and end of a field.
        """
        match self.state:
            case (States.BEGIN | States.END_OF_FIELD | States.END_OF_RECORD):
                self.doublequotes_in_field = 1
                self.transition(States.IN_FIELD)
            case States.IN_FIELD:
                if self.doublequotes_in_field == 0:
                    self._raise_field_error('Unexpected double quote found')
                self.doublequotes_in_field += 1
                self.transition(States.QUOTE_IN_FIELD)
            case States.QUOTE_IN_FIELD:
                self.doublequotes_in_field += 1
                # One cannot indefinitely defer the output of
                # literal doublequote characters until a
                # non-doublequote character is found as this
                # is a strange but valid situation:
                # ...," """""" ",...
                if self.has_unbalanced_doublequotes:
                    builder.append('"')
                self.transition(States.IN_FIELD)
            case other:
                self._raise_field_error(f'Unexpected state {other}')

    def _get_fields(self) -> Sequence[str]:
        """Returns the current fields reference and then assigns
        a brand new list to the fields variable to avoid any
        manipulation of the latter to affect the former.

        Returns:
            Sequence[str]: Current record's fields.
        """
        to_ret, self.fields = self.fields, []
        return to_ret

    def parse(self, read_from: io.TextIOBase) -> Iterable[Sequence[str]]:
        """Parses the given CSV input returning records as they
        are completed.

        Args:
            read_from (io.TextIOBase): The stream of CSV input.

        Raises:
            CsvParseException: Raised if the given text cannot
            be successfully parsed.
        """
        with StringBuilder() as builder:
            for c in each_character_of(read_from):
                match c:
                    case '"':
                        self.process_doublequote(builder)
                    case _:
                        self.process_char(c, builder)
                if self.state == States.END_OF_RECORD:
                    yield self._get_fields()
            if self.state != States.END_OF_RECORD:
                self.end_record(builder)
                yield self._get_fields()
            self.transition(States.END)
            self.record_number -= 1  # Move back to reflect final count.

    def _raise_field_error(self, msg: str) -> None:
        """Raises a CsvParseException with the current field and record numbers
        appended to the message passed in.

        Args:
            msg (str): The first part of the message for the CsvParseException.

        Raises:
            CsvParseException: The final message include field and record.
        """
        raise CsvParseException(
            f'{msg} -> field {self.field_number} of record {self.record_number}')

    def reset(self) -> None:
        """Resets the parser to its initial state."""
        super().reset()
        # Must use a new instance rather than clear to avoid manipulating
        # the caller's last record.
        self.fields = []
        self.fields_per_record = None
        self.doublequotes_in_field = 0
        self.record_number = 1
